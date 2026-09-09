import os
import sqlite3

APP_DB = "/config/app.db"


def library_arguments(library_dir):
    """calibredb arguments addressing the library.

    While the Calibre content server is running it holds the library, and calibredb
    refuses to open the same library directly. Address it through the server instead,
    which is what calibre recommends. Falls back to the library path when the content
    server is disabled or its setting cannot be read.
    """
    path_args = ["--library-path={}".format(library_dir)]
    try:
        con = sqlite3.connect("file:{}?mode=ro".format(APP_DB), uri=True, timeout=5)
        try:
            enabled, port = con.execute("select config_calibre_server_enabled, config_calibre_server_port "
                                        "from settings").fetchone()
        finally:
            con.close()
    except (sqlite3.Error, TypeError):
        return path_args
    if not enabled:
        return path_args
    return ["--with-library", "http://127.0.0.1:{}/#{}".format(port, os.path.basename(str(library_dir).rstrip("/")))]
