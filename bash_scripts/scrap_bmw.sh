FILE=./results/bmw.csv
if test -f "$FILE"; then
    cp $FILE ./results/bmw.bkp.csv
    rm -rf $FILE
fi
scrapy crawl bmw -o ./results/bmw.csv -t csv
