@echo off
cd /d "%~dp0"
echo Sincronizando el War Room C5I...
git pull origin master
git add .
git commit -m "Actualizacion automatica desde Windows"
git push origin master
echo ¡Todo listo!
pause