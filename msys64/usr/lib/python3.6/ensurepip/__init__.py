import os
import os.path
import pkgutil
import shutil
import sys
import tempfile
from ensurepip import rewheel


__all__ = ["version", "bootstrap"]


_SETUPTOOLS_VERSION = "39.2.0"

_PIP_VERSION = "10.0.1"

_SIX_VERSION = "1.10.0"

_APPDIRS_VERSION = "1.4.0"

_PACKAGING_VERSION = "16.8"

_PYPARSING_VERSION = "2.1.10"

_PROJECTS = [
    ("setuptools", _SETUPTOOLS_VERSION),
    ("pip", _PIP_VERSION),
    ("six", _SIX_VERSION),
    ("appdirs", _APPDIRS_VERSION),
    ("packaging", _PACKAGING_VERSION),
    ("pyparsing", _PYPARSING_VERSION)
]


def _run_pip(args, additional_paths=None):
    # Add our bundled software to the sys.path so we can import it
    if additional_paths is not None:
        sys.path = additional_paths + sys.path

    # Install the bundled software
    import pip._internal
    if args[0] in ["install", "list", "wheel"]:
        args.append('--pre')
    return pip._internal.main(args)


def version():
    """
    Returns a string specifying the bundled version of pip.
    """
    return _PIP_VERSION

def _disable_pip_configuration_settings():
    # We deliberately ignore all pip environment variables
    # when invoking pip
    # See http://bugs.python.org/issue19734 for details
    keys_to_remove = [k for k in os.environ if k.startswith("PIP_")]
    for k in keys_to_remove:
        del os.environ[k]
    # We also ignore the settings in the default pip configuration file
    # See http://bugs.python.org/issue20053 for details
    os.environ['PIP_CONFIG_FILE'] = os.devnull


def bootstrap(*, root=None, upgrade=False, user=False,
              altinstall=False, default_pip=False,
              verbosity=0):
    """
    Bootstrap pip into the current Python installation (or the given root
    directory).

    Note that calling this function will alter both sys.path and os.environ.
    """
    # Discard the return value
    _bootstrap(root=root, upgrade=upgrade, user=user,
               altinstall=altinstall, default_pip=default_pip,
               verbosity=verbosity)


def _bootstrap(*, root=None, upgrade=False, user=False,
              altinstall=False, default_pip=False,
              verbosity=0):
    """
    Bootstrap pip into the current Python installation (or the given root
    directory). Returns pip command status code.

    Note that calling this function will alter both sys.path and os.environ.
    """
    if altinstall and default_pip:
        raise ValueError("Cannot use altinstall and default_pip together")

    _disable_pip_configuration_settings()

    # By default, installing pip and setuptools installs all of the
    # following scripts (X.Y == running Python version):
    #
    #   pip, pipX, pipX.Y, easy_install, easy_install-X.Y
    #
    # pip 1.5+ allows ensurepip to request that some of those be left out
    if altinstall:
        # omit pip, pipX and easy_install
        os.environ["ENSUREPIP_OPTIONS"] = "altinstall"
    elif not default_pip:
        # omit pip and easy_install
        os.environ["ENSUREPIP_OPTIONS"] = "install"

    whls = []
    rewheel_dir = None
    # try to see if we have system-wide versions of _PROJECTS
    dep_records = rewheel.find_system_records([p[0] for p in _PROJECTS])
    # TODO: check if system-wide versions are the newest ones
    # if --upgrade is used?
    if all(dep_records):
        # if we have all _PROJECTS installed system-wide, we'll recreate
        # wheels from them and install those
        rewheel_dir = tempfile.TemporaryDirectory()
        for dr in dep_records:
            new_whl = rewheel.rewheel_from_record(dr, rewheel_dir.name)
            whls.append(os.path.join(rewheel_dir.name, new_whl))
    else:
        # if we don't have all the _PROJECTS installed system-wide,
        # let's just fall back to bundled wheels
        for project, version in _PROJECTS:
            whl = os.path.join(
                os.path.dirname(__file__),
                "_bundled",
                "{}-{}-py2.py3-none-any.whl".format(project, version)
            )
            whls.append(whl)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Put our bundled wheels into a temporary directory and construct the
        # additional paths that need added to sys.path
        additional_paths = []
        for whl in whls:
            shutil.copy(whl, tmpdir)
            additional_paths.append(os.path.join(tmpdir, os.path.basename(whl)))
        if rewheel_dir:
            rewheel_dir.cleanup()

        # Construct the arguments to be passed to the pip command
        args = ["install", "--no-index", "--find-links", tmpdir]
        if root:
            args += ["--root", root]
        if upgrade:
            args += ["--upgrade"]
        if user:
            args += ["--user"]
        if verbosity:
            args += ["-" + "v" * verbosity]

        return _run_pip(args + [p[0] for p in _PROJECTS], additional_paths)

def _uninstall_helper(*, verbosity=0):
    """Helper to support a clean default uninstall process on Windows

    Note that calling this function may alter os.environ.
    """
    # Nothing to do if pip was never installed, or has been removed
    try:
        import pip
    except ImportError:
        return

    # If the pip version doesn't match the bundled one, leave it alone
    if pip.__version__ != _PIP_VERSION:
        msg = ("ensurepip will only uninstall a matching version "
               "({!r} installed, {!r} bundled)")
        print(msg.format(pip.__version__, _PIP_VERSION), file=sys.stderr)
        return

    _disable_pip_configuration_settings()

    # Construct the arguments to be passed to the pip command
    args = ["uninstall", "-y", "--disable-pip-version-check"]
    if verbosity:
        args += ["-" + "v" * verbosity]

    return _run_pip(args + [p[0] for p in reversed(_PROJECTS)])


def _main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="python -m ensurepip")
    parser.add_argument(
        "--version",
        action="version",
        version="pip {}".format(version()),
        help="Show the version of pip that is bundled with this Python.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help=("Give more output. Option is additive, and can be used up to 3 "
              "times."),
    )
    parser.add_argument(
        "-U", "--upgrade",
        action="store_true",
        default=False,
        help="Upgrade pip and dependencies, even if already installed.",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        default=False,
        help="Install using the user scheme.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Install everything relative to this alternate root directory.",
    )
    parser.add_argument(
        "--altinstall",
        action="store_true",
        default=False,
        help=("Make an alternate install, installing only the X.Y versioned "
              "scripts (Default: pipX, pipX.Y, easy_install-X.Y)."),
    )
    parser.add_argument(
        "--default-pip",
        action="store_true",
        default=False,
        help=("Make a default pip install, installing the unqualified pip "
              "and easy_install in addition to the versioned scripts."),
    )

    args = parser.parse_args(argv)

    return _bootstrap(
        root=args.root,
        upgrade=args.upgrade,
        user=args.user,
        verbosity=args.verbosity,
        altinstall=args.altinstall,
        default_pip=args.default_pip,
    )