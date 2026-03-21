# Maintainer: Yunus Emre YILMAZ <yunusemreyl>
# Co-Maintainer: ja4e

pkgname=hp-laptop-manager-git
_pkgname=HP-Laptop-Manager
pkgver=1.2.1
pkgrel=1
pkgdesc="Advanced HP Omen/Victus laptop manager for Linux with RGB, Fan, and MUX control"
arch=('x86_64')
url="https://github.com/yunusemreyl/OmenCommandCenterforLinux"
license=('GPL')
depends=('python' 'python-gobject' 'gtk4' 'libadwaita' 'python-pydbus' 'python-cairo' 'dkms' 'polkit')
makedepends=('git' 'gcc' 'make' 'pkg-config')
provides=('hp-laptop-manager')
conflicts=('hp-laptop-manager')
source=('git+https://github.com/yunusemreyl/OmenCommandCenterforLinux.git')
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/${pkgname%-git}"
  git describe --long --tags | sed 's/\([^-]*-\)g/r\1/;s/-/./g' | sed 's/^v//'
}

package() {
  cd "$srcdir/${pkgname%-git}"

  # Install directories
  mkdir -p "$pkgdir/usr/share/hp-manager/gui"
  mkdir -p "$pkgdir/usr/share/hp-manager/images"
  mkdir -p "$pkgdir/usr/libexec/hp-manager"
  mkdir -p "$pkgdir/etc/hp-manager"
  mkdir -p "$pkgdir/etc/dbus-1/system.d"
  mkdir -p "$pkgdir/etc/systemd/system"
  mkdir -p "$pkgdir/usr/share/polkit-1/actions"
  mkdir -p "$pkgdir/usr/share/applications"
  mkdir -p "$pkgdir/usr/bin"

  # Daemon files
  cp -r src/daemon/* "$pkgdir/usr/libexec/hp-manager/"

  # GUI files
  cp -r src/gui/* "$pkgdir/usr/share/hp-manager/gui/"
  cp -r images/* "$pkgdir/usr/share/hp-manager/images/"

  # System files
  cp data/com.yyl.hpmanager.conf "$pkgdir/etc/dbus-1/system.d/"
  cp data/com.yyl.hpmanager.service "$pkgdir/etc/systemd/system/"
  cp data/com.yyl.hpmanager.policy "$pkgdir/usr/share/polkit-1/actions/"
  cp data/com.yyl.hpmanager.desktop "$pkgdir/usr/share/applications/"



  # Binary launcher
  cat > "$pkgdir/usr/bin/hp-manager" << EOF
#!/bin/bash
cd /usr/share/hp-manager/gui
exec python3 /usr/share/hp-manager/gui/main_window.py "\$@"
EOF
  chmod +x "$pkgdir/usr/bin/hp-manager"

  # DKMS Driver
  _dkms_dir="$pkgdir/usr/src/hp-rgb-lighting-${pkgver}"
  mkdir -p "$_dkms_dir"
  cp driver/hp-wmi.c "$_dkms_dir/"
  cp driver/hp-rgb-lighting.c "$_dkms_dir/"
  cp driver/Makefile "$_dkms_dir/"
  cp driver/dkms.conf "$_dkms_dir/"

  # Set version in dkms.conf
  sed -i "s/PACKAGE_VERSION=.*/PACKAGE_VERSION=\"${pkgver}\"/" "$_dkms_dir/dkms.conf"
}
