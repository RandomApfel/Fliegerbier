# Fliegerbier

Bot für die automatische Abrechnung von
Bier und anderen Getränken

## Dependencies
```
pip3 install python-telegram-bot
```

## Config
```ini
# config.ini
[config]

bottoken = 1296429914:AAGcl8X7i_oF6oC2AkdVtkJxZT9fIRSsXLM
database = ./fliegerbier.sql
adminchat = -1234
reverttime = 30

# Der Adminchat muss eine Gruppe sein,
# denn sonst kann der Admin keine Getränke
# bestellen.
# Außerdem macht es aus organisatorischer Sicht mehr Sinn.

```