# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2026 OzzieIsaacs
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess
import sys
import threading
import time

from . import config, constants, logger

log = logger.create()

_process = None
_lock = threading.RLock()


def library_arguments():
    """calibredb arguments addressing the library through the content server, empty when it is not running."""
    if not config.config_calibre_server_enabled or not config.config_calibre_dir:
        return []
    return ["--with-library", "http://127.0.0.1:{}/#{}".format(
        config.config_calibre_server_port, os.path.basename(config.config_calibre_dir.rstrip("/")))]


def _db_mtime(db_path):
    mtime = None
    for path in (db_path, db_path + "-wal"):
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            continue
        if mtime is None or stamp > mtime:
            mtime = stamp
    return mtime


def _watch(process, db_path):
    """Reload the content server when the library database is changed behind its back.

    calibre-server keeps the library in memory and never notices writes made
    directly to metadata.db (web UI edits, ingest, calibredb), so external
    changes stay invisible to its clients until it reloads. Restart it once
    the database has changed and then been quiet for 30 seconds, so it is
    never bounced in the middle of a burst of writes.
    """
    last = None
    changed = None
    while True:
        time.sleep(5)
        with _lock:
            if _process is not process or process.poll() is not None:
                return
        mtime = _db_mtime(db_path)
        if mtime is None:
            continue
        if last is None:
            last = mtime
        elif mtime != last:
            last = mtime
            changed = time.time()
        elif changed and time.time() - changed >= 30:
            log.info("Library database changed, reloading calibre content server")
            with _lock:
                if _process is process and process.poll() is None:
                    _locked_start()
            return


def start():
    with _lock:
        _locked_start()


def _locked_start():
    global _process
    _locked_stop()
    if not config.config_calibre_server_enabled or not config.config_calibre_dir:
        return
    binary = os.path.join(config.config_binariesdir or "",
                          "calibre-server.exe" if sys.platform == "win32" else "calibre-server")
    if not os.path.isfile(binary):
        log.error("calibre-server binary not found: %s", binary)
        return
    args = [binary, "--port", str(config.config_calibre_server_port),
            "--listen-on", config.config_calibre_server_listen or "127.0.0.1",
            "--disable-fallback-to-detected-interface",
            "--enable-local-write"]
    if config.config_calibre_server_anonymous_writes:
        if config.config_calibre_server_trusted_ips:
            args += ["--trusted-ips", config.config_calibre_server_trusted_ips]
    elif config.config_calibre_server_username and config.config_calibre_server_password_e:
        userdb = os.path.join(constants.CONFIG_DIR, "content_server_users.sqlite")
        try:
            os.remove(userdb)
        except OSError:
            pass
        result = subprocess.run([binary, "--userdb", userdb, "--manage-users", "--", "add",
                                 config.config_calibre_server_username,
                                 config.config_calibre_server_password_e],
                                capture_output=True, text=True)
        if result.returncode != 0:
            log.error("Failed to create calibre content server user: %s", result.stderr)
            return
        args += ["--enable-auth", "--auth-mode", "basic", "--userdb", userdb]
    args.append(config.config_calibre_dir)
    try:
        _process = subprocess.Popen(args)
    except OSError as ex:
        log.error("Failed to start calibre content server: %s", ex)
        _process = None
        return
    log.info("Calibre content server started on port %s", config.config_calibre_server_port)
    threading.Thread(target=_watch,
                     args=(_process, os.path.join(config.config_calibre_dir, "metadata.db")),
                     daemon=True).start()


def stop():
    with _lock:
        _locked_stop()


def _locked_stop():
    global _process
    if _process is not None and _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(10)
        except subprocess.TimeoutExpired:
            _process.kill()
        log.info("Calibre content server stopped")
    _process = None
