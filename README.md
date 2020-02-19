一.安装方法   
1.安装nginx  
rpm -Uvh http://nginx.org/packages/centos/7/noarch/RPMS/nginx-release-centos-7-0.el7.ngx.noarch.rpm  
yum install -y nginx   
systemctl start nginx.service   
systemctl enable nginx.service   
2.关闭防火墙   
setenforce 0   
sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/sysconfig/selinux   
sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config   
systemctl stop firewalld.service   
systemctl disable firewalld.service   
3.安装postgresql   
yum install -y postgresql-server postgresql-contrib   
postgresql-setup initdb   
systemctl start postgresql   
systemctl enable postgresql   
确认启动成功后，systemctl stop postgresql   
4.迁移数据库   
把data文件放入/var/lib/pgsql中，并覆盖   
chown -R postgres:postgres /var/lib/pgsql/data   
chmod 700 /var/lib/pgsql/data   
sudo systemctl start postgresql   
确认启动是否成功   
5.部署web   
把rockstor文件夹放入/opt下   
确认rockstor/bin下的文件都具有可执行权限  
（可跳过此步骤）python /opt/rockstor/bootstrap.py -c /opt/rockstor/buildout.cfg    
/opt/rockstor/bin/buildout -N -c /opt/rockstor/buildout.cfg      
命令执行到最后会启动服务，确认服务启动后，即可进入页面  
6.更新django数据库   
/opt/rockstor/bin/django makemigrations storageadmin  
(若上一步报错，则执行此命令)/opt/rockstor/bin/django makemigrations --merge       
/opt/rockstor/bin/django migrate storageadmin           
7.安装shellinabox  
yum search epel-release   
yum info epel-release   
yum install epel-release   
yum install openssl shellinabox   


二.v1.0更新   
对界面进行了汉化     
去掉了暂时无用的功能     
更改了数据库安装方式，由半创建半迁移改为完全迁移（后期会采取相对理想的方案）   
修复了一些bug    














