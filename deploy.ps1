$x = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64"
$env:PATH="$env:PATH;$x"
pyside6-deploy.exe -c .\src\pysidedeploy.spec .\src\main.py
