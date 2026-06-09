# kvm_env/dependency_manager.py
import subprocess
import os
import sys
import getpass

class DependencyManager:
    REQUIRED_PACKAGES = [
        "qemu-kvm",
        "libvirt-daemon-system",
        "libvirt-clients",
        "virtinst",
        "ansible",
        "python3-libvirt",
        "postgresql",
        "postgresql-contrib"
    ]

    _checked = False

    @classmethod
    def _skip_check(cls):
        """Пропускает проверку после первого успешного выполнения"""
        if cls._checked:
            return True
        flag_file = "/tmp/kvm-env-deps-checked"
        if os.path.exists(flag_file):
            cls._checked = True
            return True
        try:
            with open(flag_file, 'w') as f:
                f.write("1")
            cls._checked = True
        except:
            pass
        return False
    
    @classmethod
    def _check_already_done(cls):
        """Проверяет, выполнялась ли уже проверка зависимостей"""
        flag_file = "/tmp/kvm-env-deps-checked"
        if os.path.exists(flag_file):
            return True
        # Создаём файл-флаг при первом запуске
        try:
            with open(flag_file, 'w') as f:
                f.write(str(os.getpid()))
        except:
            pass
        return False

    @staticmethod
    def run_command(cmd, sudo=False, capture_output=False):
        """Запускает команду, при sudo запрашивает пароль."""
        if sudo and os.geteuid() != 0:
            cmd = ["sudo"] + cmd
        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                return result.returncode, result.stdout, result.stderr
            else:
                subprocess.run(cmd, check=True)
                return 0, "", ""
        except subprocess.CalledProcessError as e:
            return e.returncode, "", str(e)

    @classmethod
    def ensure_dependencies(cls):
        """Главный метод: проверяет и устанавливает всё необходимое."""
        print("🔍 Проверка системных зависимостей...")

        if cls._skip_check():
            return True

        # Пропускаем, если уже проверяли в этой сессии
        if cls._check_already_done():
            return True
        
        # 1. Проверка /dev/kvm
        if not os.path.exists("/dev/kvm"):
            print("⚠️  Внимание: модуль KVM не найден.")
            print("    Убедитесь, что:")
            print("    1. Виртуализация включена в BIOS")
            print("    2. Вы не в виртуальной машине (или включена nested virtualization)")
            print("    Продолжаем, но виртуальные машины не будут работать.\n")

        # 2. Проверка и установка пакетов
        missing = []
        for pkg in cls.REQUIRED_PACKAGES:
            ret, _, _ = cls.run_command(["dpkg", "-s", pkg], capture_output=True)
            if ret != 0:
                missing.append(pkg)

        if missing:
            print(f"📦 Устанавливаем отсутствующие пакеты: {', '.join(missing)}")
            cls.run_command(["apt", "update"], sudo=True)
            ret, _, err = cls.run_command(["apt", "install", "-y"] + missing, sudo=True, capture_output=True)
            if ret != 0:
                print(f"❌ Ошибка установки пакетов: {err}")
                sys.exit(1)
            print("✅ Все пакеты установлены.")

        # 3. Проверка службы libvirtd
        ret, _, _ = cls.run_command(["systemctl", "is-active", "libvirtd"], capture_output=True)
        if ret != 0:
            print("▶️  Запускаем службу libvirtd...")
            cls.run_command(["systemctl", "enable", "libvirtd"], sudo=True)
            cls.run_command(["systemctl", "start", "libvirtd"], sudo=True)

        # 4. Проверка службы PostgreSQL
        ret, _, _ = cls.run_command(["systemctl", "is-active", "postgresql"], capture_output=True)
        if ret != 0:
            print("▶️  Запускаем службу PostgreSQL...")
            cls.run_command(["systemctl", "enable", "postgresql"], sudo=True)
            cls.run_command(["systemctl", "start", "postgresql"], sudo=True)

        # 5. Проверка группы libvirt
        username = getpass.getuser()
        ret, out, _ = cls.run_command(["groups", username], capture_output=True)
        if "libvirt" not in out:
            print(f"👤 Добавляем пользователя {username} в группу libvirt...")
            cls.run_command(["usermod", "-aG", "libvirt", username], sudo=True)
            print("⚠️  Для применения изменений выйдите и зайдите заново.")

        # 6. Проверка группы kvm
        if "kvm" not in out:
            print(f"👤 Добавляем пользователя {username} в группу kvm...")
            cls.run_command(["usermod", "-aG", "kvm", username], sudo=True)

        print("✅ Проверка зависимостей завершена")
        return True
