FILE=./results/valley_motor.csv
if test -f "$FILE"; then
    cp $FILE ./results/valley_motor.bkp.csv
    rm -rf $FILE
fi
scrapy crawl valley_motor -o ./results/valley_motor.csv -t csv
