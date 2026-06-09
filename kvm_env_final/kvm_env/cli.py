#!/usr/bin/env python3
# kvm_env/cli.py
import click
import sys
import os
from .dependency_manager import DependencyManager
from .config_manager import ConfigManager
from .vm_manager import VMManager
from .image_builder import ImageBuilder

# Глобальные объекты
config = None
vm_mgr = None
img_builder = None

def init_managers():
    global config, vm_mgr, img_builder
    if config is None:
        try:
            config = ConfigManager()
            config.init_db()
            vm_mgr = VMManager(config)
            img_builder = ImageBuilder(config)
        except Exception as e:
            click.secho(f"Ошибка инициализации: {e}", fg='red', err=True)
            sys.exit(1)

@click.group()
def cli():
    """Управление воспроизводимой виртуальной экосистемой KVM"""
    # Проверка зависимостей (только 1 раз за всё время)
    DependencyManager.ensure_dependencies()
    init_managers()

@cli.command()
def build_image():
    """Собрать базовый образ через Packer"""
    click.echo("📦 Сборка базового образа...")
    try:
        result = img_builder.build_image()
        if result:
            click.secho("✅ Образ успешно собран", fg='green')
        else:
            click.secho("⚠️ Сборка образа не выполнена", fg='yellow')
    except Exception as e:
        click.secho(f"❌ Ошибка: {e}", fg='red', err=True)
        sys.exit(1)

@cli.command()
@click.argument("name")
@click.option("--vcpus", default=1, help="Количество виртуальных CPU")
@click.option("--memory", default=512, help="Объём RAM в MB")
@click.option("--description", default="", help="Описание ВМ")
def create(name, vcpus, memory, description):
    """Создать новую виртуальную машину"""
    try:
        vm_mgr.create_vm(name, vcpus, memory, description)
        click.secho(f"✅ ВМ {name} создана", fg='green')
    except Exception as e:
        click.secho(f"❌ Ошибка: {e}", fg='red', err=True)
        sys.exit(1)

@cli.command()
@click.argument("name")
@click.option("--vcpus", type=int, help="Новое количество vCPU")
@click.option("--memory", type=int, help="Новый объём RAM в MB")
@click.option("--description", help="Новое описание")
def edit(name, vcpus, memory, description):
    """Изменить параметры существующей ВМ"""
    try:
        vm_mgr.edit_vm(name, vcpus, memory, description)
        click.secho(f"✅ ВМ {name} изменена", fg='green')
    except Exception as e:
        click.secho(f"❌ Ошибка: {e}", fg='red', err=True)
        sys.exit(1)

@cli.command()
@click.argument("source")
@click.argument("destination")
def clone(source, destination):
    """Клонировать виртуальную машину"""
    try:
        vm_mgr.clone_vm(source, destination)
        click.secho(f"✅ ВМ {source} склонирована в {destination}", fg='green')
    except Exception as e:
        click.secho(f"❌ Ошибка: {e}", fg='red', err=True)
        sys.exit(1)

@cli.command()
def list():
    """Список всех виртуальных машин"""
    try:
        vms = vm_mgr.list_vms()
        if not vms:
            click.echo("📋 Нет виртуальных машин")
            return
        
        click.echo("\n" + "=" * 80)
        click.echo(f"{'Имя':<20} {'Состояние':<12} {'vCPU':<6} {'Память(MB)':<12} Описание")
        click.echo("-" * 80)
        for vm in vms:
            state_color = 'green' if vm['state'] == 'running' else 'yellow'
            click.echo(f"{vm['name']:<20} ", nl=False)
            click.secho(f"{vm['state']:<12}", fg=state_color, nl=False)
            click.echo(f"{vm['vcpus']:<6} {vm['memory_mb']:<12} {vm.get('description', '')}")
        click.echo("=" * 80 + "\n")
    except Exception as e:
        click.secho(f"❌ Ошибка: {e}", fg='red', err=True)
        sys.exit(1)

@cli.command()
@click.argument("name")
@click.option("--remove-disk", is_flag=True, help="Удалить файл диска")
@click.option("--force", is_flag=True, help="Не запрашивать подтверждение")
def remove(name, remove_disk, force):
    """Удалить виртуальную машину"""
    if not force:
        click.confirm(f"Вы уверены, что хотите удалить ВМ {name}?", abort=True)
        if remove_disk:
            click.confirm("Удалить диск? Это необратимо.", abort=True)
    try:
        vm_mgr.delete_vm(name, remove_disk)
        click.secho(f"✅ ВМ {name} удалена", fg='green')
    except Exception as e:
        click.secho(f"❌ Ошибка: {e}", fg='red', err=True)
        sys.exit(1)

@cli.command()
@click.argument("name")
@click.option("--playbook", required=True, help="Путь к Ansible плейбуку")
@click.option("--user", default="root", help="Пользователь для подключения")
def provision(name, playbook, user):
    """Запустить Ansible плейбук внутри ВМ"""
    try:
        vm_mgr.provision_vm(name, playbook, user)
        click.secho(f"✅ Провижининг ВМ {name} выполнен", fg='green')
    except Exception as e:
        click.secho(f"❌ Ошибка: {e}", fg='red', err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()
