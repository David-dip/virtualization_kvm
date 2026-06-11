# 🖥️ KVM Environment Manager

<div align="center">

**Управление воспроизводимой виртуальной экосистемой на базе KVM**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Debian](https://img.shields.io/badge/Debian-12|13-red.svg)](https://www.debian.org/)
[![KVM](https://img.shields.io/badge/KVM-QEMU-orange.svg)](https://www.linux-kvm.org/)

</div>

---

## 📋 О проекте

**KVM Environment Manager** — это CLI-приложение для управления виртуальными машинами на базе гипервизора KVM.

### Основные возможности

| Команда | Описание |
|---------|----------|
| `create` | Создание виртуальной машины из базового образа |
| `list` | Вывод списка всех ВМ с их состоянием |
| `edit` | Изменение параметров ВМ (vCPU, память, описание) |
| `clone` | Клонирование ВМ с новым UUID и MAC-адресом |
| `remove` | Удаление ВМ (опционально с диском) |
| `provision` | Настройка ВМ через Ansible playbook |
| `build-image` | Автоматическая сборка базового образа через Packer |

### Ключевые особенности

- ✅ **Автоустановка зависимостей** — приложение само установит qemu-kvm, libvirt, ansible, packer, postgresql
- ✅ **Воспроизводимость** — перенос экосистемы на новый хост одной командой
- ✅ **Логирование** — все операции сохраняются в PostgreSQL
- ✅ **Модульная архитектура** — легко расширять и тестировать

---

## 🛠️ Технологический стек

| Компонент | Технология |
|-----------|------------|
| Язык программирования | Python 3.11+ |
| CLI-фреймворк | Click |
| Гипервизор | KVM / QEMU (через libvirt) |
| База данных | PostgreSQL |
| Управление конфигурациями | Ansible |
| Сборка образов | Packer |
| Целевая ОС хоста | Debian 12 (Bookworm) / 13 (Trixie) |

---

## 📦 Установка

### Системные требования

- Процессор с поддержкой аппаратной виртуализации (Intel VT-x / AMD-V)
- 8+ GB оперативной памяти (рекомендуется 16 GB)
- 50 GB свободного дискового пространства
- Debian 12/13 с правами sudo

### Быстрая установка

```bash
# 1. Клонируем репозиторий
git clone https://github.com/yourusername/kvm-env.git
cd kvm-env

# 2. Создаём виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# 3. Устанавливаем приложение
pip install -e .

# 4. Настраиваем PostgreSQL
sudo -u postgres psql << EOF
CREATE USER kvm_user WITH PASSWORD 'your_password';
CREATE DATABASE kvm_env OWNER kvm_user;
GRANT ALL PRIVILEGES ON DATABASE kvm_env TO kvm_user;
EOF

# 5. Создаём файл конфигурации
cat > .env << EOF
PGHOST=localhost
PGPORT=5432
PGDATABASE=kvm_env
PGUSER=kvm_user
PGPASSWORD=your_password
EOF

# 6. Устанавливаем Packer (если нужна сборка образов)
wget https://releases.hashicorp.com/packer/1.11.2/packer_1.11.2_linux_amd64.zip
unzip packer_1.11.2_linux_amd64.zip
sudo mv packer /usr/local/bin/



---
# Базовые команды
# Создание виртуальной машины
kvm-env create web-server --vcpus 2 --memory 2048 --description "Production web server"

# Просмотр списка ВМ
kvm-env list

# Редактирование параметров
kvm-env edit web-server --vcpus 4 --memory 4096

# Клонирование ВМ
kvm-env clone web-server web-server-backup

# Удаление ВМ (с диском)
kvm-env remove web-server-backup --remove-disk --force

# Ansible провижининг
kvm-env provision web-server --playbook setup.yml --user root

# Сборка базового образа через Packer
kvm-env build-image

---

## Пример вывода kvm-env list
================================================================================
Имя                  Состояние    vCPU   Память(MB)   Описание
--------------------------------------------------------------------------------
web-server           running      4      4096         Production web server
database             stopped      8      8192         PostgreSQL server
================================================================================


kvm-env/
├── setup.py                 # Установка пакета
├── requirements.txt         # Python-зависимости
├── .env.example            # Шаблон конфигурации БД
├── README.md               # Документация
│
└── kvm_env/
    ├── __init__.py
    ├── cli.py              # Точка входа, обработка команд CLI
    ├── dependency_manager.py   # Автоустановка зависимостей (apt, systemctl)
    ├── config_manager.py   # Работа с PostgreSQL (CRUD, логирование)
    ├── vm_manager.py       # Управление ВМ через libvirt
    └── image_builder.py    # Сборка образов через Packer
