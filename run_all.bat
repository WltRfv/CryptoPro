@echo off
chcp 65001 > nul
title CryptoPro + Blockchain - Complete System

echo ===============================================
echo    ЗАПУСК CRYPTOPRO КОШЕЛЬКА И БЛОКЧЕЙН СИСТЕМЫ
echo ===============================================
echo.

:: Проверка структуры папок
if not exist MainProject (
    echo ❌ Папка MainProject не найдена!
    echo Создайте папку MainProject и поместите туда файлы блокчейн реестра
    pause
    exit /b 1
)

:: Запрос портов
set /p blockchain_port="Введите порт для блокчейн реестра (5000-5010, по умолчанию 5000): "
if "%blockchain_port%"=="" set blockchain_port=5000

set /p cryptopro_port="Введите порт для CryptoPro кошелька (5001-5010, по умолчанию 5001): "
if "%cryptopro_port%"=="" set cryptopro_port=5001

echo.
echo ===============================================
echo 🚀 НАСТРОЙКИ ЗАПУСКА
echo ===============================================
echo Блокчейн реестр: localhost:%blockchain_port%
echo CryptoPro кошелек: localhost:%cryptopro_port%
echo.

:: Запуск блокчейн реестра в отдельном окне
echo Запуск блокчейн реестра...
start "Blockchain Ledger" cmd /k "cd MainProject && call run.bat --port %blockchain_port%"

:: Ждем немного перед запуском кошелька
timeout /t 5 /nobreak > nul

:: Запуск CryptoPro кошелька
echo Запуск CryptoPro кошелька...
python run.py --port %cryptopro_port% --blockchain-port %blockchain_port%

echo.
echo ===============================================
echo Система остановлена
echo ===============================================
pause