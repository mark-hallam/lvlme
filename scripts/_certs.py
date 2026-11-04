"""Website certificates: one retry with the computer's own certificate file, then one plain line.

Python from python.org on a Mac has no certificate file of its own until its
"Install Certificates.command" has been run, so every https link fails with
CERTIFICATE_VERIFY_FAILED. The scripts that read links pass their opener here.
On a certificate failure it retries once with a context built from the
system's certificate file (/etc/ssl/cert.pem, which macOS ships), or from
certifi when that package happens to be installed (it is never required).
If that fails too, it raises CertificateProblem, whose text is one plain line
saying what to do. Certificate checking is never turned off: the retry uses
ssl.create_default_context, which checks the certificate and the host name.

This module never opens a connection itself; the caller's opener does.
"""
import os
import ssl

SYSTEM_CA_FILES = ("/etc/ssl/cert.pem",)
HELP = ("Your Python can't check website certificates. If you installed Python from python.org, run "
        "'Install Certificates.command' in its Applications folder, then try again.")
PASTE_INSTEAD = "Or paste the job ad text instead."


class CertificateProblem(Exception):
    """The site's certificate could not be checked, even with the system's certificate file. One plain line.

    >>> str(CertificateProblem()) == HELP
    True
    """

    def __init__(self, tail=""):
        super().__init__(HELP + (" " + tail if tail else ""))


def is_cert_error(exc):
    """True when exc (or the reason inside it) is a failed certificate check.

    >>> is_cert_error(ssl.SSLCertVerificationError("certificate verify failed"))
    True
    >>> is_cert_error(OSError("connection refused"))
    False
    """
    for e in (exc, getattr(exc, "reason", None)):
        if isinstance(e, ssl.SSLCertVerificationError):
            return True
        if isinstance(e, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(e):
            return True
    return False


def ca_file():
    """The first certificate file to retry with: the system's, else certifi's when installed, else None."""
    for path in SYSTEM_CA_FILES:
        if os.path.isfile(path):
            return path
    try:
        import certifi  # optional, never required
    except ImportError:
        return None
    path = certifi.where()
    return path if os.path.isfile(path) else None


def retry_context():
    """A checking SSL context from ca_file(), or None when there is no certificate file to use."""
    path = ca_file()
    return ssl.create_default_context(cafile=path) if path else None


def open_checked(opener, req, timeout, tail=""):
    """opener(req, timeout=timeout); on a certificate failure, retry once with retry_context().

    Raises CertificateProblem (one plain line, with tail added) when the retry is not possible or fails
    the same way. Any other error is raised unchanged.
    """
    try:
        return opener(req, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 (only certificate failures are handled; the rest re-raise)
        if not is_cert_error(exc):
            raise
        first = exc
    context = retry_context()
    if context is None:
        raise CertificateProblem(tail) from first
    try:
        return opener(req, timeout=timeout, context=context)
    except Exception as exc:  # noqa: BLE001
        if is_cert_error(exc):
            raise CertificateProblem(tail) from exc
        raise
