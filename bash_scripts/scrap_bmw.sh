FILE=../results/bmw.csv
if test -f "$FILE"; then
    mv $FILE ../results/bmw.bkp.csv
fi
scrapy crawl bmw -o ../results/bmw.csv -t csv
