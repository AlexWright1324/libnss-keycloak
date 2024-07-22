import os, sys

class DebugLogger:
    def __init__(self):
        pass

    def __enter__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        if os.getenv("debug") is None:
            self.file = open("/tmp/libnss-keycloak.log", 'a')
            sys.stdout = self.file
            sys.stderr = self.file
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def output(self, string: str):
        print(string, file=self.original_stdout)