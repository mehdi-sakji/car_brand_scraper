FILE=./results/city_motor.csv
if test -f "$FILE"; then
    mv $FILE ./results/city_motor.bkp.csv
fi
scrapy crawl city_motor -o ./results/city_motor.csv -t csv
