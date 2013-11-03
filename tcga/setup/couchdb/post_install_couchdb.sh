# change file ownership from root to couchdb user and adjust permissions
useradd -d /usr/local/var/lib/couchdb couchdb
chown -R couchdb: /usr/local/var/lib/couchdb /usr/local/var/log/couchdb /usr/local/var/run/couchdb /usr/local/etc/couchdb /usr/local/lib/couchdb /usr/local/share/couchdb
chmod 0770 /usr/local/var/lib/couchdb /usr/local/var/log/couchdb /usr/local/var/run/couchdb /usr/local/lib/couchdb /usr/local/share/couchdb
chmod 664 /usr/local/etc/couchdb/*.ini 
chmod 775 /usr/local/etc/couchdb/*.d

# start couchdb
cd /etc/init.d
ln -s /usr/local/etc/init.d/couchdb couchdb
/etc/init.d/couchdb start
# Start couchdb on system start
update-rc.d couchdb defaults

# Verify couchdb is running
curl http://127.0.0.1:5984/