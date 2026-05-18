#!/bin/bash
cd "$(dirname "$0")"
echo "Sincronizando el War Room C5I..."
git pull origin master
git add .
git commit -m "Actualizacion automatica desde Mac"
git push origin master
echo "¡Todo listo! Cierra esta ventana."