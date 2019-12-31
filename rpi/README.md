## Install instructions

Flash raspbian-buster-lite. Modify the boot files:

    $ cat <<EOF > /Volumes/boot/wpa_supplicant.conf
    ctrl_interface=/var/run/wpa_supplicant
    country=US
    
    network={
        ssid="<SSID>"
        psk="<KEY>"
    }
    EOF

    $ cat <<EOF >> /Volumes/boot/config.txt
    
    # fixes rpi4 ttyAMA0 serial console
    dtoverlay=miniuart-bt
    enable_uart=1

    # speedups
    disable_splash=1
    boot_delay=0
    force_turbo=1
    dtparam=sd_overclock=100
    EOF
    
    $ touch /Volumes/boot/ssh

Log in (pi@raspberrypi.local).
Run raspi-config, set hostname, change password.
Add ssh key.

Run ansible script.

    $ ansible-playbook deploy.yml

## Deploy

    $ rpi/deploy
