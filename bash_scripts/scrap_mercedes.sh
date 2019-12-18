FILE=../results/mercedes.csv
if test -f "$FILE"; then
    mv $FILE ../results/mercedes.bkp.csv
fi
scrapy crawl mercedes -o ../results/mercedes.csv -t csv
