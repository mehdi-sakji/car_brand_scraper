FILE=../results/nissan.csv
if test -f "$FILE"; then
    mv $FILE ../results/nissan.bkp.csv
fi
scrapy crawl nissan -o ../results/nissan.csv -t csv
