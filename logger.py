#!/usr/bin/env python
import subprocess
import sys
import os

# tee writes to both a file and a stream at the same time
class Tee:
    def __init__(self, filename, stream):
        try:
            self.file = open(filename, 'a')
        except PermissionError:
            if os.path.exists(filename):
                os.remove(filename)
                self.file = open(filename, 'a')
            else:
                raise
        self.stream = stream

    def write(self, message):
        self.file.write(message)
        self.stream.write(message)
        self.file.flush()
        self.stream.flush()

    def flush(self):
        self.file.flush()
        self.stream.flush()

    def isatty(self):
        return self.stream.isatty()


def log_command(cmd, **kwargs):
    """Run a command and log its execution in real-time."""
    print(f"\n[EXEC] {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    # Check if we need to return the output (like for lsblk)
    if kwargs.get('capture_output'):
        kwargs.pop('capture_output')
        try:
            output = subprocess.check_output(cmd, text=True, **kwargs)
            print(output)
            return type('Result', (), {'stdout': output})()
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Command failed with return code {e.returncode}")
            raise

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            **kwargs
        )

        for line in process.stdout:
            print(line, end='')

        process.wait()

        if process.returncode != 0:
            print(f"[ERROR] Command failed with return code {process.returncode}")
            raise subprocess.CalledProcessError(process.returncode, cmd)

        return type('Result', (), {'returncode': 0})()
    except Exception as e:
        if not isinstance(e, subprocess.CalledProcessError):
            print(f"[ERROR] Execution failed: {e}")
        raise
