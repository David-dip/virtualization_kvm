# kvm_env/image_builder.py
import os
import subprocess
import json
import tempfile

class ImageBuilder:
    def __init__(self, config_manager):
        self.config = config_manager

    def build_image(self, iso_url=None, output_path="/var/lib/libvirt/images/debian12-base.qcow2"):
        print("🔨 Начинаем сборку базового образа...")
        
        try:
            subprocess.run(['packer', '--version'], capture_output=True, text=True, check=True)
        except:
            print("❌ Packer не установлен")
            return False

        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"📁 Временная директория: {tmpdir}")
            
            template = {
                "builders": [{
                    "type": "qemu",
                    "iso_url": iso_url or "https://cdimage.debian.org/mirror/cdimage/archive/12.5.0/amd64/iso-cd/debian-12.5.0-amd64-netinst.iso",
                    "iso_checksum": "none",
                    "output_directory": os.path.join(tmpdir, "output-qemu"),
                    "disk_size": 10240,
                    "memory": 2048,
                    "format": "qcow2",
                    "headless": True,
                    "ssh_username": "root",
                    "ssh_password": "debian",
                    "ssh_timeout": "60m",
                    "boot_wait": "5s",
                    "boot_command": [
                        "<esc><wait>",
                        "install <wait>",
                        "auto=true <wait>",
                        "priority=critical <wait>",
                        "url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/preseed.cfg <wait>",
                        "<enter>"
                    ],
                    "http_directory": tmpdir,
                    "shutdown_command": "echo 'debian' | sudo -S shutdown -P now"
                }],
                "provisioners": [{
                    "type": "shell",
                    "inline": [
                        "apt-get update",
                        "apt-get install -y openssh-server qemu-guest-agent",
                        "systemctl enable ssh"
                    ]
                }]
            }
            
            template_path = os.path.join(tmpdir, "template.json")
            with open(template_path, 'w') as f:
                json.dump(template, f, indent=2)
            print("✅ Шаблон создан")

            preseed = '''#### Локализация и язык
d-i debian-installer/locale string en_US
d-i keyboard-configuration/xkb-keymap select us
d-i console-setup/ask_detect boolean false
d-i console-setup/layoutcode string us

#### Сеть (настройка через DHCP)
d-i netcfg/choose_interface select auto
d-i netcfg/get_hostname string debian
d-i netcfg/get_domain string local

#### Зеркало для установки
d-i mirror/country string manual
d-i mirror/http/hostname string deb.debian.org
d-i mirror/http/directory string /debian
d-i mirror/suite string bookworm

#### Часовой пояс
d-i time/zone string UTC
d-i clock-setup/utc boolean true
d-i clock-setup/ntp boolean true

#### Пользователи (работаем от root)
d-i passwd/root-login boolean true
d-i passwd/root-password password debian
d-i passwd/root-password-again password debian
d-i passwd/make-user boolean false

#### ★★★ РАЗМЕТКА ДИСКА (ИСПРАВЛЕННАЯ ВЕРСИЯ) ★★★
# Используем проверенный рецепт 'multi' для избежания ошибки partman.
d-i partman-auto/method string regular
d-i partman-auto/disk string /dev/vda
d-i partman-auto/choose_recipe select multi

# Рецепт 'multi' создает /boot и корневой раздел, а также опционально swap.
# Он гарантирует наличие rootfs.
d-i partman-partitioning/confirm_write_new_label boolean true
d-i partman/choose_partition select finish
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true

# Этот параметр автоматически ответит "No" на вопрос о создании swap.
d-i partman-basicfilesystems/no_swap boolean false
d-i partman/confirm_no_swap boolean true

#### Базовая система и пакеты
d-i base-installer/kernel/image string linux-image-amd64
d-i pkgsel/include string openssh-server,qemu-guest-agent
d-i pkgsel/upgrade select full-upgrade

#### APT (пропускаем вопрос о дополнительном установочном носителе)
d-i apt-setup/cdrom/set-first boolean false
d-i apt-setup/services-select multiselect security, updates

#### Установка загрузчика GRUB
d-i grub-installer/only_debian boolean true
d-i grub-installer/with_other_os boolean true
d-i grub-installer/bootdev string /dev/vda

#### Завершение установки
d-i finish-install/reboot_in_progress note
d-i debian-installer/exit/poweroff boolean true
'''
            preseed_path = os.path.join(tmpdir, "preseed.cfg")
            with open(preseed_path, 'w') as f:
                f.write(preseed)
            print("✅ preseed.cfg создан")

            print("🚀 Запуск Packer... (10-20 минут)")
            process = subprocess.Popen(
                ['packer', 'build', template_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                print(line, end='')
            
            if process.wait() != 0:
                print("❌ Ошибка сборки")
                return False

            generated_image = None
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.qcow2'):
                        generated_image = os.path.join(root, file)
                        break
                if generated_image:
                    break
            
            if not generated_image:
                print("❌ Образ не найден")
                return False
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            subprocess.run(['cp', generated_image, output_path], check=True)
            subprocess.run(['chmod', '660', output_path], check=True)
            self.config.save_image(output_path, "built with packer")
            print(f"✅ Образ сохранён: {output_path}")
            return output_path
