FILE=./results/nissan.csv
if test -f "$FILE"; then
    cp $FILE ./results/nissan.bkp.csv
    rm -rf $FILE
fi
scrapy crawl nissan -o ./results/nissan.csv -t csv
