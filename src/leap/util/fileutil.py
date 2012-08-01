from itertools import chain
import os
import platform
import stat


def is_user_executable(fpath):
    st = os.stat(fpath)
    return bool(st.st_mode & stat.S_IXUSR)


def extend_path():
    ourplatform = platform.system()
    if ourplatform == "Linux":
        return "/usr/local/sbin:/usr/sbin"
    # XXX add mac / win extended search paths?


def which(program):
    """
    an implementation of which
    that extends the path with
    other locations, like sbin
    (f.i., openvpn binary is likely to be there)
    @param program: a string representing the binary we're looking for.
    """
    def is_exe(fpath):
        """
        check that path exists,
        it's a file,
        and is executable by the owner
        """
        # we would check for access,
        # but it's likely that we're
        # using uid 0 + polkitd

        return os.path.isfile(fpath)\
            and is_user_executable(fpath)

    def ext_candidates(fpath):
        yield fpath
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    def iter_path(pathset):
        """
        returns iterator with
        full path for a given path list
        and the current target bin.
        """
        for path in pathset.split(os.pathsep):
            exe_file = os.path.join(path, program)
            #print 'file=%s' % exe_file
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate):
                    yield candidate

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        # extended iterator
        # with extra path
        extended_path = chain(
            iter_path(os.environ["PATH"]),
            iter_path(extend_path()))
        for candidate in extended_path:
            if candidate is not None:
                return candidate

    # sorry bro.
    return None