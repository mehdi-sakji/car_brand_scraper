FILE=../results/f3_motor.csv
if test -f "$FILE"; then
    mv $FILE ../results/f3_motor.bkp.csv
fi
scrapy crawl f3_motor -o ../results/f3_motor.csv -t csv
