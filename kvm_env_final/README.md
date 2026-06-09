# KVM Environment Manager

Управление воспроизводимой виртуальной экосистемой на базе KVM.

## Установка
# Клонировать или скопировать проект
cd ~/kvm-env

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -e .
