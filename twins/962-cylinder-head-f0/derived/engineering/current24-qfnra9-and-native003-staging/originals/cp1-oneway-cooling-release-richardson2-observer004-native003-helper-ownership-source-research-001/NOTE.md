# Non-reaping helper ownership: primary-source decision

This is source research only. No owner, actual, admission, wrapper or runtime
probe is implemented here. The selected native3.12 executable remains an expected
identity; no executable, alias, extension, provider or scientific body was read,
hashed or queried. The reviewed staging/freshness helpers remain unchanged.

`os.waitid` is unavailable in CPython3.12.11 on Apple platforms. Both its pinned
[implementation](https://github.com/python/cpython/blob/v3.12.11/Modules/posixmodule.c#L8755)
and [documentation](https://github.com/python/cpython/blob/v3.12.11/Doc/library/os.rst#L4332)
exclude this route. A capability assertion followed by unavoidable refusal would
not produce a usable owner. Apple exposes a C waitid/WNOWAIT interface in its
[public header](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/wait.h#L151)
and preserves an exited child when WNOWAIT is requested in
[current public kernel source](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_exit.c#L2984).
That does not add a Python binding. No ctypes structure, raw syscall, numeric
waitpid flag or unsupported fallback is proposed; public main is not proof of the
installed kernel or ABI.

The supported Python API candidate is `select.kqueue`/`select.kevent` with
KQ_FILTER_PROC and KQ_NOTE_EXIT. Their pinned3.12.11
[documentation](https://github.com/python/cpython/blob/v3.12.11/Doc/library/select.rst#L92)
and [exports](https://github.com/python/cpython/blob/v3.12.11/Modules/selectmodule.c#L2497)
describe kernel event notification. The
[Apple kqueue manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/kqueue.2.html)
distinguishes exit from reap. Its API applies changes before returning events and
reports change errors. Pinned Python does not export KQ_EV_RECEIPT: use documented
ADD/ENABLE/ONESHOT, an event capacity of one, and preserve/reject errors or unknown
events. Do not add NOTE_TRACK: Apple's
[public implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_event.c#L1031)
rejects that branch. This proposal needs only the known direct child's exit event.

An immediate post-Popen registration has an exit race: Apple's process filter
can return ESRCH if the process is already gone. The proposed remedy is the small
stop-before-exec protocol below. The
[Apple wait manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/wait.2.html)
supports WUNTRACED stop reporting; a stopped status is not a terminal reap. The
initial call must target exactly the owned PID, never all children.

Proposed protocol, conditional on separate root source approval:

1. Before creating a child, bind exact owner/wrapper/helper/plan/control identities,
   selected original3.12 route, -B-I-S and thread1. Validate named kqueue/constants
   and create the queue before launch. Set SIGCHLD to SIG_DFL and retain the old
   disposition for disclosure. Install the bounded stop latch. There is no ps,
   provider discovery or additional metadata query.
2. Popen creates exactly one new-session Python wrapper. It imports only the fixed
   minimal standard modules, stops itself with SIGSTOP before any helper/query
   execution, then after continuation execs the exact selected3.12 helper argv in
   the same PID. It neither forks a supervisor subtree nor changes the helper.
3. Root uses bounded `waitpid(owned_PID, WUNTRACED|WNOHANG)` until the exact SIGSTOP
   status. It verifies SID=PGID=owned_PID, records that ownership certificate,
   registers KQ_FILTER_PROC/NOTE_EXIT while stopped, rejects registration errors,
   then uses raw SIGCONT on that same unreaped direct PID. Early terminal status
   is setup failure; no helper/query has been authorized by the handshake alone.
4. Retain the Popen object strongly and use only bounded kqueue event waits while
   monitoring permitted output metadata and stop/deadline conditions. No poll,
   wait, communicate, Popen context manager, destructor path or Popen signal
   method may consume status before cleanup. An exit event is notification only;
   raw terminal status is obtained later from the exact child.
5. On abnormal exit/stop/deadline, finish any group signals while that direct child
   is still unreaped. The certificate plus no-reap invariant retains the owned
   PID/session anchor. Verify no ownership-changing branch exists in the wrapper,
   helpers or query. Then explicitly wait/reap once and require postreap ESRCH.
   EPERM/unknown remains error; do not reinterpret it as absence or use it as a
   prefilter. If ownership was never established or was lost, do not signal a
   guessed group. Preserve incomplete cleanup rather than fabricate success.
6. For normal exit, require the full positive operation receipt and source-defined
   query reaping where applicable, then obtain raw child0, wait/reap and require
   the whole owned group absent. The root's complete final time/byte checks and
   outer0 remain independent. Any nonzero, incomplete stream or late failure is
   refusal. A receipt alone is not status or cleanup proof.

The no-reap invariant must cover implicit Python behavior. Pinned
[Popen source](https://github.com/python/cpython/blob/v3.12.11/Lib/subprocess.py#L994)
waits on context exit and polls in its destructor; poll/wait consume terminal
status, and send_signal/terminate/kill can poll too. Keep the object referenced,
avoid these paths until the deliberate reap, and create no unrelated Popen
instances in the owner. There must be no competing waiter or SIGCHLD reaper.

[POSIX status rules](https://pubs.opengroup.org/onlinepubs/9699919799/functions/V2_chap02.html#tag_15_13)
make SIG_IGN/SA_NOCLDWAIT incompatible with retaining waitable status. In pinned
CPython, [signal.signal](https://github.com/python/cpython/blob/v3.12.11/Modules/signalmodule.c#L494)
uses [PyOS_setsig](https://github.com/python/cpython/blob/v3.12.11/Python/pylifecycle.c#L2975),
whose sigaction flags omit SA_NOCLDWAIT. Resetting SIGCHLD before the sole child
therefore supplies the intended source-level disposition on this route; this is
not an observation of the selected executable's installed behavior.

All protocol startup, handshake, helper, query, cleanup and serialization remain
inside the existing whole60s limit. Cleanup reserve must be allocated within it;
TERM8s is not an added wall-time allowance. The unchanged query bound is5s and
complete inclusive output is32MiB including1,213,802 staged bytes, separate staging
receipt, logs and external controls. No sampled RSS or hard quota pass is claimed.
Staging and freshness still need distinct admissions and results; native100/115/
TERM10/2GiB/512MiB/growth32MiB and every scientific gate remain unchanged.

The primary sources support this as a concrete source-design candidate. Installed
select API/origin identity, exact wrapper/owner implementation and failure-path
review remain future gates. No native retry or execution authority follows.
