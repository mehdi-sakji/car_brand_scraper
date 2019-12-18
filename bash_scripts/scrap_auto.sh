FILE=../results/auto.csv
if test -f "$FILE"; then
    mv $FILE ../results/auto.bkp.csv
fi
scrapy crawl auto -o ../results/auto.csv -t csv
