FILE=../results/valley_motor.csv
if test -f "$FILE"; then
    mv $FILE ../results/valley_motor.bkp.csv
fi
scrapy crawl valley_motor -o ../results/valley_motor.csv -t csv
