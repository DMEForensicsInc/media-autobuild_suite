@echo off

setlocal
set HG=%~f0

set PYTHONHOME=
set in=%*
set out=%in: {= "{%
set out=%out:} =}" %

%~dp0python2 %~dp0hg %out%
