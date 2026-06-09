# kvm_env/vm_manager.py
import os
import uuid
import libvirt
import subprocess
import time
import xml.etree.ElementTree as ET

class VMManager:
    def __init__(self, config_manager):
        self.config = config_manager
        try:
            self.conn = libvirt.open('qemu:///system')
            if self.conn is None:
                raise Exception("Не удалось подключиться к libvirt")
        except Exception as e:
            print(f"⚠️  Не удалось подключиться к libvirt: {e}")
            print("   Виртуальные машины не будут работать, но БД доступна.")
            self.conn = None

    def _generate_xml(self, name, vcpus, memory_mb, disk_path, mac_addr=None):
        """Генерация XML определения домена"""
        if not mac_addr:
            mac_addr = "52:54:00:" + ":".join([f"{x:02x}" for x in os.urandom(3)])
        return f"""<domain type='kvm'>
  <name>{name}</name>
  <memory unit='MiB'>{memory_mb}</memory>
  <currentMemory unit='MiB'>{memory_mb}</currentMemory>
  <vcpu placement='static'>{vcpus}</vcpu>
  <os>
    <type arch='x86_64' machine='pc-q35-7.2'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
  </features>
  <cpu mode='host-passthrough' check='none'/>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{disk_path}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <mac address='{mac_addr}'/>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'/>
  </devices>
</domain>"""

    def create_vm(self, name, vcpus, memory_mb, description):
        # Проверяем, существует ли уже
        if self.config.get_vm(name):
            raise Exception(f"ВМ с именем {name} уже существует")

        # Базовый образ
        img_info = self.config.get_current_image()
        if not img_info:
            print("⚠️  Базовый образ не найден. Создаю запись без диска (только для БД).")
            disk_path = f"/var/lib/libvirt/images/{name}.qcow2"
            vm_id = self.config.add_vm(name, description, vcpus, memory_mb, disk_path, 'stopped')
            self.config.log_operation("create", vm_id, True)
            print(f"✅ Запись о ВМ {name} добавлена в БД (реальный диск не создан)")
            return

        disk_path = f"/var/lib/libvirt/images/{name}.qcow2"
        
        # Копируем образ
        try:
            subprocess.run(["cp", img_info['image_path'], disk_path], check=True)
            subprocess.run(["chmod", "660", disk_path], check=True)
        except Exception as e:
            print(f"⚠️  Не удалось скопировать диск: {e}")
            vm_id = self.config.add_vm(name, description, vcpus, memory_mb, disk_path, 'stopped')
            self.config.log_operation("create", vm_id, True)
            print(f"✅ Запись о ВМ {name} добавлена в БД (диск не скопирован)")
            return

        # Создаём домен в libvirt
        if self.conn:
            xml_desc = self._generate_xml(name, vcpus, memory_mb, disk_path)
            dom = self.conn.defineXML(xml_desc)
            vm_id = self.config.add_vm(name, description, vcpus, memory_mb, disk_path, 'stopped')
            self.config.log_operation("create", vm_id, True)
            print(f"✅ ВМ {name} создана")
        else:
            vm_id = self.config.add_vm(name, description, vcpus, memory_mb, disk_path, 'stopped')
            self.config.log_operation("create", vm_id, True)
            print(f"✅ Запись о ВМ {name} добавлена в БД (libvirt недоступен)")

    def edit_vm(self, name, vcpus=None, memory_mb=None, description=None):
        vm = self.config.get_vm(name)
        if not vm:
            raise Exception(f"ВМ {name} не найдена")

        # Обновляем БД
        self.config.update_vm(name, vcpus=vcpus, memory_mb=memory_mb, description=description)
        
        # Если libvirt доступен, обновляем домен
        if self.conn:
            try:
                dom = self.conn.lookupByName(name)
                if dom.isActive():
                    dom.destroy()
                dom.undefine()
                new_xml = self._generate_xml(name, 
                                            vcpus or vm['vcpus'], 
                                            memory_mb or vm['memory_mb'], 
                                            vm['disk_path'])
                self.conn.defineXML(new_xml)
            except Exception as e:
                print(f"⚠️  Не удалось обновить домен в libvirt: {e}")
        
        self.config.log_operation("edit", vm['id'], True)
        print(f"✅ ВМ {name} изменена")

    def clone_vm(self, source, destination):
        src = self.config.get_vm(source)
        if not src:
            raise Exception(f"Исходная ВМ {source} не найдена")
        if self.config.get_vm(destination):
            raise Exception(f"ВМ {destination} уже существует")

        dst_disk = f"/var/lib/libvirt/images/{destination}.qcow2"
        
        # Копируем диск
        try:
            if os.path.exists(src['disk_path']):
                subprocess.run(["cp", src['disk_path'], dst_disk], check=True)
                subprocess.run(["chmod", "660", dst_disk], check=True)
        except Exception as e:
            print(f"⚠️  Не удалось скопировать диск: {e}")

        # Создаём домен
        if self.conn:
            new_xml = self._generate_xml(destination, src['vcpus'], src['memory_mb'], dst_disk)
            self.conn.defineXML(new_xml)
        
        vm_id = self.config.add_vm(destination, src['description'], src['vcpus'], src['memory_mb'], dst_disk, 'stopped')
        self.config.log_operation("clone", vm_id, True)
        print(f"✅ ВМ {source} склонирована в {destination}")

    def delete_vm(self, name, remove_disk=False):
            vm = self.config.get_vm(name)
            if not vm:
                raise Exception(f"ВМ {name} не найдена")
            
            vm_id = vm['id']  # Сохраняем ID до удаления записи
            
            # Удаляем из libvirt
            if self.conn:
                try:
                    dom = self.conn.lookupByName(name)
                    if dom.isActive():
                        dom.destroy()
                    dom.undefine()
                except:
                    pass
            
            # Удаляем диск
            if remove_disk and os.path.exists(vm['disk_path']):
                os.remove(vm['disk_path'])
                print(f"🗑️  Диск {vm['disk_path']} удалён")
            
            # Удаляем связанные логи (важно: сначала логи, потом ВМ)
            with self.config.conn.cursor() as cur:
                cur.execute("DELETE FROM operation_log WHERE vm_id = %s", (vm_id,))
                self.config.conn.commit()
            
            # Удаляем из БД
            self.config.delete_vm(name)
            
            print(f"✅ ВМ {name} удалена")

    def list_vms(self):
        vms_from_db = self.config.get_all_vms()
        
        # Обновляем состояние из libvirt
        if self.conn:
            for vm in vms_from_db:
                try:
                    dom = self.conn.lookupByName(vm['name'])
                    state = "running" if dom.isActive() else "stopped"
                    if vm['state'] != state:
                        self.config.update_vm(vm['name'], state=state)
                        vm['state'] = state
                except:
                    pass
        return vms_from_db

    def provision_vm(self, name, playbook_path, user='root'):
        vm = self.config.get_vm(name)
        if not vm:
            raise Exception(f"ВМ {name} не найдена")
        
        if not self.conn:
            raise Exception("libvirt недоступен, провижининг невозможен")
        
        # Получить IP ВМ
        dom = self.conn.lookupByName(name)
        if not dom.isActive():
            dom.create()
            print("⏳ Ожидаем запуска ВМ...")
            time.sleep(30)
        
        # Получить IP через virsh domifaddr
        result = subprocess.run(['virsh', 'domifaddr', name], capture_output=True, text=True)
        ip = None
        for line in result.stdout.split('\n'):
            if 'ipv4' in line.lower():
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[3].split('/')[0]
                    break
        
        if not ip:
            raise Exception("Не удалось определить IP ВМ")
        
        print(f"🌐 IP адрес ВМ: {ip}")
        print(f"🚀 Запуск Ansible плейбука {playbook_path}...")
        
        # Формируем команду Ansible с запросом пароля
        cmd = [
            'ansible-playbook', 
            '-i', f'{ip},', 
            '-u', user, 
            '--ask-pass',
            '--ssh-common-args=-o StrictHostKeyChecking=no', 
            playbook_path
        ]
        
        # Запускаем с передачей пароля через stdin
        subprocess.run(cmd, check=True)
        
        self.config.log_operation("provision", vm['id'], True)
        print(f"✅ Провижининг ВМ {name} выполнен")
