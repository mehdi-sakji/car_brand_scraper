FILE=../results/audi.csv
if test -f "$FILE"; then
    mv $FILE ../results/audi.bkp.csv
fi
scrapy crawl audi -o ../results/audi.csv -t csv
