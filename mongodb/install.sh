#!/bin/bash

centos() #TODO: fails on centos7
{
  yum update

  releasever=8

  cat > /etc/yum.repos.d/mongodb-org-4.2.repo <<EOF
[mongodb-org-4.2]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/4.2/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-4.2.asc
EOF

  # The following complains that requires libssl.so.1.1()(64bit) libssl.so.1.1(OPENSSL_1_1_0)(64bit) libc.so.6(GLIBC_2.18)(64bit) libcrypto.so.1.1()(64bit) libcrypto.so.1.1(OPENSSL_1_1_0)(64bit)
  # yum install -y mongodb-org --skip-broken
  yum install -y mongodb-org
}

ubuntu() # requires wget and gnupg
{
  wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | apt-key add -
  echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.2 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.2.list
  apt-get update
  apt-get install -y mongodb-org
  service mongod start
}

ubuntu
