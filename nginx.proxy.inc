proxy_set_header      Host              $http_host;
proxy_set_header      X-Forwarded-By    $server_addr:$server_port;
proxy_set_header      X-Forwarded-For   $remote_addr;
proxy_set_header      X-Real-IP         $remote_addr;
proxy_set_header      CLIENT_IP         $remote_addr;

proxy_pass_request_headers on;
proxy_redirect off;
client_max_body_size 100M;
proxy_buffering off;
proxy_request_buffering off;
proxy_pass http://lab-server:8000;
