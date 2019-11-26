#!/usr/bin/python

import sys
import argparse
import uuid
import subprocess
import re
import time,datetime
import functools
import pprint
import json
#from xml.etree import ElementTree as ET
import socket
import os
import signal
import threading
import fcntl
import logging
import logging.handlers
import ConfigParser
import StringIO
import os.path


EXE_ROOT_DIR = os.environ['PROTO'] if 'PROTO' in os.environ else ""

def calltrace(fn):
    # Unpack function's arg count, arg names, arg defaults
    code = fn.func_code
    argcount = code.co_argcount
    argnames = code.co_varnames[:argcount]
    fn_defaults = fn.func_defaults or list()
    argdefs = dict(zip(argnames[-len(fn_defaults):], fn_defaults))

    def format_arg_value(arg_val):
        """ Return a string representing a (name, value) pair.

        >>> format_arg_value(('x', (1, 2, 3)))
        'x=(1, 2, 3)'
        """
        arg, val = arg_val
        return "%s=%r" % (arg, val)

    @functools.wraps(fn)
    def wrapped(*v, **k):
        if not k.get("nologging", False):
            # Collect function arguments by chaining together positional,
            # defaulted, extra positional and keyword arguments.
            positional = map(format_arg_value, zip(argnames, v))
            defaulted = [format_arg_value((a, argdefs[a]))
                         for a in argnames[len(v):] if a not in k]
            nameless = map(repr, v[argcount:])
            keyword = map(format_arg_value, k.items())
            args = positional + defaulted + nameless + keyword
            logging.getLogger().debug("%s(%s)" % (fn.__name__,", ".join(args)))
        return fn(*v, **k)
    return wrapped

@calltrace
def run_command2(command, shell=False, add_prefix=False, nologging=False):
    if add_prefix:
        if isinstance(cmd, str):
            cmd = EXE_ROOT_DIR + cmd
        else:
            cmd[0] = EXE_ROOT_DIR + cmd[0]

    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         close_fds = True,
                         shell=shell)

    return iter(p.stdout.readline, b'')

@calltrace
def shell_check_call(cmd, nologging=False):
    subprocess.check_call(cmd, shell=True, close_fds = True)

@calltrace
def shell_call(cmd, quiet=True, add_prefix=False, timeout=None, data=None, nologging=False):
    if add_prefix:
        if isinstance(cmd, str):
            cmd = EXE_ROOT_DIR + cmd
        else:
            cmd[0] = EXE_ROOT_DIR + cmd[0]

    cmd = Command(cmd, shell=True)
    out, err = cmd.run(data=data, timeout = timeout)
    if not nologging:
        logging.getLogger().debug(err + out)
    if not quiet:
        print err + out
    return err + out

@calltrace
def shell_call_rc(cmd, quiet=True, add_prefix=False, timeout=None, data=None, nologging=False, executable=None):
    if add_prefix:
        if isinstance(cmd, str):
            cmd = EXE_ROOT_DIR + cmd
        else:
            cmd[0] = EXE_ROOT_DIR + cmd[0]
    cmd = Command(cmd, shell=True)
    out, err = cmd.run(data=data, timeout = timeout, executable=executable)
    return_code = cmd.returncode
    if not nologging:
        logging.getLogger().debug("%d:%s%s" % (return_code, err, out))
    if not quiet:
        print err + out
    return (err + out, return_code)

@calltrace
def shell_call_rc_sp(cmd, sp, quiet=True, add_prefix=False, timeout=None, data=None, nologging=False, executable="/usr/bin/pfksh"):
    if add_prefix:
        if isinstance(cmd, str):
            cmd = EXE_ROOT_DIR + cmd
        else:
            cmd[0] = EXE_ROOT_DIR + cmd[0]
    if is_ha_env() and sp != my_spname() and (sp == "uspa" or sp == "uspb"):
        cmd = "/usr/bin/ssh -l admin -q -o ConnectTimeout=10 -o 'StrictHostKeyChecking=no' -i /etc/ha_id_dsa %s %s" \
            % ("_ha_uspa" if sp == "uspa" else "_ha_uspb", cmd)
    cmd = Command(cmd, shell=True)
    out, err = cmd.run(data=data, timeout = timeout, executable=executable)
    return_code = cmd.returncode
    if not nologging:
        logging.getLogger().debug("%d:%s%s" % (return_code, err, out))
    if not quiet:
        print err + out
    return (err + out, return_code)

@calltrace
def shell_call_rc_peer(cmd, quiet=True, add_prefix=False, timeout=None, data=None, nologging=False):
    if add_prefix:
        if isinstance(cmd, str):
            cmd = EXE_ROOT_DIR + cmd
        else:
            cmd[0] = EXE_ROOT_DIR + cmd[0]
    cmd = "/usr/bin/ssh -l admin -q -o ConnectTimeout=10 -o 'StrictHostKeyChecking=no' -i /etc/ha_id_dsa %s %s" \
        % ("_ha_uspb" if my_spname() == "uspa" else "_ha_uspa", cmd)
    cmd = Command(cmd, shell=True)
    out, err = cmd.run(timeout = timeout, data=data)
    return_code = cmd.returncode
    if not nologging:
        logging.getLogger().debug("%d:%s%s" % (return_code, err, out))
    if not quiet:
        print err + out
    return (err + out, return_code)

#/usr/bin/ssh -t -l admin -q -o ConnectTimeout=10 -o 'StrictHostKeyChecking=no' -i /etc/ha_id_dsa _ha_uspa "$*"
def _terminate_process(process):
    if sys.platform == 'win32':
        import ctypes
        PROCESS_TERMINATE = 1
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, process.pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(process.pid, signal.SIGTERM)

def _kill_process(process):
   if sys.platform == 'win32':
       _terminate_process(process)
   else:
       os.kill(process.pid, signal.SIGKILL)

def _is_alive(thread):
    if hasattr(thread, "is_alive"):
        return thread.is_alive()
    else:
        return thread.isAlive()


class Command(object):
    """
    wrapper to implemnt timed call
    """
    def __init__(self, cmd, shell=True):
        self.cmd = cmd
        self.shell=shell
        self.process = None
        self.out = None
        self.err = None
        self.returncode = None
        self.data = None
        self.exc = None

    def run(self, data=None, timeout=None, kill_timeout=None, env=None, cwd=None, executable=None):
        self.data = data
        self.executable = executable;
        environ = dict(os.environ)
        environ.update(env or {})

        def target():

            try:
                if self.executable:
                    self.process = subprocess.Popen(self.cmd,
                                                    universal_newlines=True,
                                                    shell=self.shell,
                                                    env=environ,
                                                    stdin=subprocess.PIPE,
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE,
                                                    executable=self.executable,
                                                    bufsize=0,
                                                    close_fds = True,
                                                    cwd=cwd,
                                                    )
                else:
                    self.process = subprocess.Popen(self.cmd,
                                                    universal_newlines=True,
                                                    shell=self.shell,
                                                    env=environ,
                                                    stdin=subprocess.PIPE,
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE,
                                                    bufsize=0,
                                                    close_fds = True,
                                                    cwd=cwd,
                                                    )


                if sys.version_info[0] >= 3:
                    self.out, self.err = self.process.communicate(
                        input = bytes(self.data, "UTF-8") if self.data else None
                    )
                else:
                    self.out, self.err = self.process.communicate(self.data)
            except Exception as exc:
                self.exc = exc


        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if self.exc:
            raise self.exc
        if _is_alive(thread) :
            _terminate_process(self.process)
            thread.join(kill_timeout)
            self.err = "command timeout."
            if _is_alive(thread):
                _kill_process(self.process)
                thread.join()
        self.returncode = self.process.returncode
        return self.out, self.err

class ICIArgparser(argparse.ArgumentParser):

    def print_usage(self, file=None):
        if file is None:
            file = sys.stdout

        # retrieve subparsers from parser
        subparsers_actions = [
            action for action in self._actions
            if isinstance(action, argparse._SubParsersAction)]
        # there will probably only be one subparser_action,
        # but better save than sorry
        self._print_message("usage:\n", file)
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice, subparser in subparsers_action.choices.items():
                #print("Subparser '{}'".format(choice))
                if subparser.usage and subparser.usage == argparse.SUPPRESS:
                    continue
                self._print_message(re.sub("^usage: ", "    ", subparser.format_usage()), file)


    def print_help(self, file=None):
        if file is None:
            file = sys.stdout

        self._print_message(self.format_help(), file)

        # retrieve subparsers from parser
        subparsers_actions = [
            action for action in self._actions
            if isinstance(action, argparse._SubParsersAction)]
        # there will probably only be one subparser_action,
        # but better save than sorry
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice, subparser in subparsers_action.choices.items():
                #print("Subparser '{}'".format(choice))
                self._print_message("------------------------------------\n", file)
                self._print_message(subparser.format_help(), file)

def parser_seqdata_dict(iterobj, starter, spliter, array_keys=[]):
    """
    parser the date int
     starter | spliter | groupkey
     key | spliter | value
     key | spliter | value
     ...
     starter | spliter | groupkey
     key | spliter | value
     key | spliter | value
     ...
     ...
    The result will be a two level dictionary
    """
    result = dict()
    start_pattern = starter
    current = None
    for line in iterobj:
        line = line.strip()
        try:
            (k,v) = re.split(spliter, line, 1)
            k = k.strip()
            v = v.strip()
            if k == start_pattern:
                current = v
                result[current] = dict()
                for kk in array_keys:
                    result[current][kk] = []

            elif current:
                if k in array_keys:
                    if k not in result[current]:
                        result[current][k] = []
                    result[current][k].append(v)
                else:
                    result[current][k] = v
        except ValueError:
            continue
    return result

def parser_seqdata_array(iterobj, starter, spliter, root_key=None, array_keys=[]):
    """
    parser the date int
     starter | spliter | groupkey
     key | spliter | value
     key | spliter | value
     ...
     starter | spliter | groupkey
     key | spliter | value
     key | spliter | value
     ...
     ...
    The result will be a list of dictionary
    """
    result = []
    start_pattern = starter
    for line in iterobj:
        line = line.strip()
        try:
            (k,v) = re.split(spliter, line, 1)
            k = k.strip()
            v = v.strip()
            if k == start_pattern:
                result.append(dict())
                if root_key:
                    result[-1][root_key] = v
                else:
                    result[-1][k] = v
                for kk in array_keys:
                    result[-1][kk] = []

            elif result:
                if k in array_keys:
                    if k not in result[-1]:
                        result[-1][k] = []
                    result[-1][k].append(v)
                else:
                    result[-1][k] = v
        except ValueError:
            continue
    return result

def tail(f, n, offset=None):
    """Reads a n lines from f with an offset of offset lines.  The return
    value is a tuple in the form ``(lines, has_more)`` where `has_more` is
    an indicator that is `True` if there are more lines in the file.
    """
    avg_line_length = 74
    to_read = n + (offset or 0)

    while 1:
        try:
            f.seek(-(avg_line_length * to_read), 2)
        except IOError:
            # woops.  apparently file is smaller than what we want
            # to step back, go to the beginning instead
            f.seek(0)
        pos = f.tell()
        lines = f.read().splitlines()
        if len(lines) >= to_read or pos == 0:
            return lines[-to_read:offset and -offset or None], \
                   len(lines) > to_read or pos > 0
        avg_line_length *= 1.3

def try_flock(path, pgid=False):
    """
    @summary: open / create file at "path" and try to flock it
    @return: fd, fd < 0 is failed
    @note: the caller should preserve the fd, so the file won't be closed
    """
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    if fd < 0:
        return -1

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        os.close(fd)
        return -1

    if pgid:
        os.write(fd, "%d" % os.getpgid(0))
        os.fsync(fd)
    return fd

def try_blflock(path, pgid=False):
    """
    @summary: open / create file at "path" and try to flock it
    @return: fd, fd < 0 is failed
    @note: the caller should preserve the fd, so the file won't be closed
    """
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    if fd < 0:
        return -1

    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except IOError:
        os.close(fd)
        return -1

    if pgid:
        os.write(fd, "%d" % os.getpgid(0))
        os.fsync(fd)
    return fd

def try_unflock(path):
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    if fd < 0:
        return -1
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except IOError:
        os.close(fd)
        return -1
    os.close(fd)
    return fd

class FLOCK(object):
    def __init__(self, name):
        self.fd = os.open(name, os.O_RDWR | os.O_CREAT)
    def lock(self):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX)
            return True
        except:
            return False
    def unlock(self):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            return True
        except:
            return False
        self.fd.close()

def go_background(lockpid=None, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
	"""
	do the UNIX double-fork magic, see Stevens' "Advanced
	Programming in the UNIX Environment" for details (ISBN 0201563177)
	http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16

        lockpid: a path to the pid lockfile, if set will try flock this file and write the pgid to it.
        @note: the caller should preserve the returned fd, so the file won't be closed
	"""
	try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
	except OSError, e:
            logging.getLogger().info("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

	# decouple from parent environment
	os.chdir("/")
	os.setsid()
	os.umask(0)
	# do second fork
	try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
	except OSError, e:
            logging.getLogger().info("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

	# redirect standard file descriptors
	sys.stdout.flush()
	sys.stderr.flush()
	si = file(stdin, 'r')
	so = file(stdout, 'a+')
	se = file(stderr, 'a+', 0)
	os.dup2(si.fileno(), sys.stdin.fileno())
	os.dup2(so.fileno(), sys.stdout.fileno())
	os.dup2(se.fileno(), sys.stderr.fileno())

        # single instance?
        fd = 0
        if lockpid:
            fd = try_flock(lockpid, pgid = True)
        return fd

def tgmk(value, base = 1000, fmt="%.2f%s"):
    """
    convert number of bytes to TB, GB, MB, KB, B
    """
    suffixs = ['B', 'KB', 'MB', 'GB', 'TB']
    base = float(base)
    for s in suffixs:
        if value < base or s == 'TB':
            return fmt % (value, s)
        value = value/base
    raise Exception("Unreachable code")

def tgmk_rvs(s, base = 1000):
    """
    convert TB, GB, MB, KB, B to number of bytes
    """
    base = float(base)
    m = re.match(r"([\d\.]+)([PTGMKB])B?$", s.upper())
    if not m:
        return int(float(s))
    if m.group(2) == 'B':
        return int(float(m.group(1)))
    if m.group(2) == 'K':
        return int(float(m.group(1)) * base)
    if m.group(2) == 'M':
        return int(float(m.group(1)) * base * base)
    if m.group(2) == 'G':
        return int(float(m.group(1)) * base * base * base)
    if m.group(2) == 'T':
        return int(float(m.group(1)) * base * base * base * base)
    if m.group(2) == 'P':
        return int(float(m.group(1)) * base * base * base * base * base)

# HA relatives
SP_NAME_FILE = "/.b/spname"
my_sp_name = None

def is_ha_env():
    return os.path.isfile(SP_NAME_FILE)

def my_spname():
    global my_sp_name
    if not os.path.exists(SP_NAME_FILE):
        return ""
    if not my_sp_name:
        with open(SP_NAME_FILE) as f:
            my_sp_name = f.read().strip()
    return my_sp_name


def test():
    pprint.pprint(parser_seqdata_dict(run_command2(["cat", "/tmp/o"]), "LU Name", "\s*:\s*"))
    pprint.pprint(parser_seqdata_dict(run_command2(["cat", "/tmp/o2"]), "View Entry", "\s*:\s*"))


if __name__ == "__main__":
    test()


# system wide param parser
# print sysparam("HA.o1", "default");
# print sysparam("HA.SecureStonith", True, bool);

_sysparam_cfg = None
def sysparam(name, default, datatype=str, refresh=False):
    global _sysparam_cfg;
    try:
        if (not _sysparam_cfg) or refresh:
            _sysparam_cfg = ConfigParser.ConfigParser()
            _sysparam_cfg.read('/etc/sysparam.conf')
        section, option = name.split(".", 1)
        if datatype == int:
            ret = _sysparam_cfg.getint(section, option);
        elif datatype == float:
            ret = _sysparam_cfg.getfloat(section, option)
        elif datatype == bool:
            ret = _sysparam_cfg.getboolean(section, option)
        else:
            ret = _sysparam_cfg.get(section, option)
        return ret
    except:
        return default

def sysparam_items(section, refresh=False):
    global _sysparam_cfg;
    try:
        if (not _sysparam_cfg) or refresh:
            _sysparam_cfg = ConfigParser.ConfigParser()
            _sysparam_cfg.read('/etc/sysparam.conf')
        return _sysparam_cfg.items(section)
    except:
        return []

def sysparam_set(name, value, save=True):
    global _sysparam_cfg;
    try:
        if not _sysparam_cfg:
            _sysparam_cfg = ConfigParser.ConfigParser()
            _sysparam_cfg.read('/etc/sysparam.conf')
        section, option = name.split(".", 1)
        if not _sysparam_cfg.has_section(section):
            _sysparam_cfg.add_section(section)
        _sysparam_cfg.set(section, option, value)
        if save:
            with open('/etc/sysparam.conf', 'wb') as f:
                _sysparam_cfg.write(f)
        return True
    except:
        logging.getLogger().debug("syspram set failed.", exc_info=True)
        return False

class SectionlessConfigParser(ConfigParser.RawConfigParser):
    """
    Extends ConfigParser to allow files without sections.

    This is done by wrapping read files and prepending them with a placeholder
    section, which defaults to '__config__'
    example:
        cfg2 = SectionlessConfigParser()
        cfg2.read("/tmp/vsftpd.conf")
        print cfg2.items(None)
        cfg2.set(None, "testadd", "xxxx")
        with open('/tmp/example.cfg', 'wb') as f:
        cfg2.write(f)
    """

    def __init__(self, *args, **kwargs):
        default_section = kwargs.pop('default_section', None)
        ConfigParser.RawConfigParser.__init__(self, *args, **kwargs)

        self._default_section = None
        self.set_default_section(default_section or '__config__')

    def get_default_section(self):
        return self._default_section

    def set_default_section(self, section):
        self.add_section(section)

        # move all values from the previous default section to the new one
        try:
            default_section_items = self.items(self._default_section)
            self.remove_section(self._default_section)
        except ConfigParser.NoSectionError:
            pass
        else:
            for (key, value) in default_section_items:
                self.set(section, key, value)

        self._default_section = section

    def read(self, filenames):
        if isinstance(filenames, basestring):
            filenames = [filenames]

        read_ok = []
        for filename in filenames:
            try:
                with open(filename) as fp:
                    self.readfp(fp)
            except IOError:
                continue
            else:
                read_ok.append(filename)

        return read_ok

    def readfp(self, fp, *args, **kwargs):
        stream = StringIO.StringIO()

        try:
            stream.name = fp.name
        except AttributeError:
            pass

        stream.write('[' + self._default_section + ']\n')
        stream.write(fp.read())
        stream.seek(0, 0)

        return ConfigParser.RawConfigParser.readfp(self, stream, *args,
                                                   **kwargs)

    def write(self, fp):
        # Write the items from the default section manually and then remove them
        # from the data. They'll be re-added later.
        try:
            default_section_items = self.items(self._default_section)
            self.remove_section(self._default_section)

            for (key, value) in default_section_items:
                fp.write("{0}={1}\n".format(key, value))

            fp.write("\n")
        except ConfigParser.NoSectionError:
            pass

        ConfigParser.RawConfigParser.write(self, fp)

        self.add_section(self._default_section)
        for (key, value) in default_section_items:
            self.set(self._default_section, key, value)

    def items(self, section):
        if section is None:
            section = self._default_section
        return ConfigParser.RawConfigParser.items(self, section)

    def get(self, section, option):
        if section is None:
            section = self._default_section
        return ConfigParser.RawConfigParser.get(self, section, option)

    def getint(self, section, option):
        if section is None:
            section = self._default_section
        return ConfigParser.RawConfigParser.getint(self, section, option)

    def getfloat(self, section, option):
        if section is None:
            section = self._default_section
        return ConfigParser.RawConfigParser.getfloat(self, section, option)

    def getboolean(self, section, option):
        if section is None:
            section = self._default_section
        return ConfigParser.RawConfigParser.getboolean(self, section, option)

    def set(self, section, option, value):
        if section is None:
            section = self._default_section
        return ConfigParser.RawConfigParser.set(self, section, option, value)


def is_model_AS():
    try:
        with open("/.b/.model") as f:
            if re.search(r"Hermes\s+AS\d\d\d\d", f.read()):
                return True
    except:
        pass
    return False


