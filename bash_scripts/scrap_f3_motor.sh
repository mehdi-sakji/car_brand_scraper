FILE=./results/f3_motor.csv
if test -f "$FILE"; then
    cp $FILE ./results/f3_motor.bkp.csv
    rm -rf $FILE
fi
scrapy crawl f3_motor -o ./results/f3_motor.csv -t csv
