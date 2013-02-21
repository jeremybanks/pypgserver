#!/usr/bin/env python
import os
import os.path
import shutil
import subprocess
import tempfile
import time

class PostgresServer(object):
    def __init__(self, data_dir=None):
        if data_dir is not None:
            self.data_dir = data_dir
            self.data_dir_is_temp = False
            try:
                must_initialize = not os.listdir(self.data_dir)
            except OSError:
                os.mkdir(self.data_dir)
                must_initialize = True
        else:
            self.data_dir = tempfile.mkdtemp()
            must_initialize = True
            self.data_dir_is_temp = True
        
        self.socket_dir = tempfile.mkdtemp()

        if must_initialize:
            subprocess.Popen([
                "pg_ctl", "init",
                "-D", self.data_dir
            ]).communicate()

        self.process = subprocess.Popen([
            "postgres",
            "-D", self.data_dir,
            "-h", "",
            "-k", self.socket_dir
        ])

        # Wait for server's socket to appear
        while len(os.listdir(self.socket_dir)) == 0:
            time.sleep(0.05)

    DEFAULT_DB_NAME = "data"

    def psycopg2_connect(self, database=None):
        import psycopg2

        database = database or self.DEFAULT_DB_NAME

        prep_connection = psycopg2.connect(
            host=self.socket_dir,
            database="template1"
        )
        try:
            prep_connection.autocommit = True
            prep_cursor = prep_connection.cursor()
            prep_cursor.execute("CREATE DATABASE \"{0}\";".format(
                database.replace("\"", "\"\"")))
        except psycopg2.ProgrammingError:
            "I hope this is because the database already exists!"
        finally:
            prep_connection.close()

        connection = psycopg2.connect(
            host=self.socket_dir,
            database=database
        )

        return connection

    def __del__(self):
        self.process.terminate()
        self.process.communicate()
        shutil.rmtree(self.socket_dir)
        if self.data_dir_is_temp:
            shutil.rmtree(self.data_dir)

def main(data_dir=None):
    # If you system fails to allocated shared memory,
    # you may need to increase the limits, as on OS X:
    #    sudo sysctl -w kern.sysv.shmall=65536
    #    sudo sysctl -w kern.sysv.shmmax=16777216

    pg = PostgresServer(data_dir)

    connection = pg.psycopg2_connect()
    cursor = connection.cursor()
    
    cursor.execute("CREATE TABLE IF NOT EXISTS times ( time int )");
    cursor.execute("INSERT INTO times( time ) VALUES ( %s )", [int(time.time())])
    cursor.execute("SELECT time FROM times")   
    print cursor.fetchall()

    connection.commit()
    connection.close()

if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv[1:]))
