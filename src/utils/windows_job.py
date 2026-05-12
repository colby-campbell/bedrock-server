import ctypes

"""
Windows Job Object helpers for binding a child process's lifetime to the parent process.
Chosen over using an import to avoid adding a dependecy, especially for users on non-Windows platforms.
"""

_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000    # from winnt.h
_JobObjectExtendedLimitInformation = 9              # from JOBOBJECTINFOCLASS enum in winnt.h


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    """Mirror of JOBOBJECT_BASIC_LIMIT_INFORMATION from winnt.h; field order and types must match exactly"""
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _IO_COUNTERS(ctypes.Structure):
    """Mirror of IO_COUNTERS from winnt.h; required as a field in _JOBOBJECT_EXTENDED_LIMIT_INFORMATION"""
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    """Mirror of JOBOBJECT_EXTENDED_LIMIT_INFORMATION from winnt.h; passed to SetInformationJobObject"""
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def create_job_object(process_handle: int) -> int | None:
    """
    Create a Windows Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE and assign
    the given process to it. Returns the job handle (keep it alive), or None on failure.
    """
    kernel32 = ctypes.windll.kernel32
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = kernel32.SetInformationJobObject(
        job,
        _JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ok:
        kernel32.CloseHandle(job)
        return None
    ok = kernel32.AssignProcessToJobObject(job, process_handle)
    if not ok:
        kernel32.CloseHandle(job)
        return None
    return job


def close_job_object(job: int) -> None:
    """Close a Windows Job Object handle created by create_job_object."""
    ctypes.windll.kernel32.CloseHandle(job)
