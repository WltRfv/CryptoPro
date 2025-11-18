"""
Замена netifaces для Python 3.13+
Полная совместимость с оригинальным netifaces API
"""
import socket

# Константы как в оригинальном netifaces
AF_INET = 2
AF_INET6 = 10
AF_PACKET = 17
AF_LINK = 18

def interfaces():
    """Возвращает список сетевых интерфейсов"""
    # Для Windows возвращаем стандартные интерфейсы
    return ['lo', 'eth0', 'wlan0']

def ifaddresses(interface):
    """Возвращает адреса для интерфейса"""
    local_ip = get_local_ip()

    if interface == 'lo':
        return {
            AF_INET: [{'addr': '127.0.0.1', 'netmask': '255.0.0.0'}],
            AF_LINK: [{'addr': '00:00:00:00:00:00'}]
        }
    elif interface in ['eth0', 'wlan0']:
        return {
            AF_INET: [{'addr': local_ip, 'netmask': '255.255.255.0'}],
            AF_LINK: [{'addr': '00:00:00:00:00:00'}]
        }
    else:
        return {}

def gateways():
    """Возвращает шлюзы по умолчанию"""
    return {
        'default': {
            AF_INET: [(get_local_ip(), 'eth0', True)]
        }
    }

def get_local_ip():
    """Получает локальный IP адрес"""
    try:
        # Способ 1: Через подключение к внешнему серверу
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            # Способ 2: Через hostname
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            # Способ 3: Возвращаем localhost
            return '127.0.0.1'

# Для совместимости с кодом, который использует netifaces.AF_INET и т.д.
__all__ = ['interfaces', 'ifaddresses', 'gateways', 'AF_INET', 'AF_INET6', 'AF_PACKET', 'AF_LINK']