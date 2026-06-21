import os
import re
import requests
import pandas as pd

from bs4 import BeautifulSoup
from datetime import timedelta

# ==================================================
# CONFIG
# ==================================================

URL_MB = "https://xskt.com.vn/xsmb/200-ngay"
URL_MT = "https://xskt.com.vn/xsmt/200-ngay"
URL_MN = "https://xskt.com.vn/xsmn/200-ngay"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )
}

# ==================================================
# TELEGRAM
# ==================================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    print(url)

    r = requests.post(
        url,
        json={
            "chat_id": str(CHAT_ID),
            "text": message
        },
        timeout=30
    )

    print("Status:", r.status_code)
    print("Response:", r.text)
    
# ==================================================
# MB
# ==================================================

def scrape_mb():

    html = requests.get(
        URL_MB,
        headers=HEADERS,
        timeout=30
    ).text

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    records = []

    tables = soup.find_all(
        "table",
        class_="result"
    )

    for table in tables:

        dock = table.find(
            "i",
            class_="dockq"
        )

        if dock is None:
            continue

        data_url = dock.get(
            "data-url",
            ""
        )

        m = re.search(
            r"(\d{2}-\d{2}-\d{4})",
            data_url
        )

        if not m:
            continue

        draw_date = pd.to_datetime(
            m.group(1),
            format="%d-%m-%Y"
        )

        for em in table.find_all("em"):

            number = re.sub(
                r"\D",
                "",
                em.get_text()
            )

            if number:

                records.append([
                    draw_date,
                    "MB",
                    number
                ])

        for p in table.find_all("p"):

            numbers = re.findall(
                r"\d+",
                p.get_text(
                    " ",
                    strip=True
                )
            )

            for number in numbers:

                records.append([
                    draw_date,
                    "MB",
                    number
                ])

    return pd.DataFrame(
        records,
        columns=[
            "Date",
            "Region",
            "Number"
        ]
    )

# ==================================================
# MT / MN
# ==================================================

def scrape_mtmn(
    url,
    region
):

    html = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    ).text

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    records = []

    tables = soup.find_all(
        "table",
        class_=lambda x:
        x and "tbl-xsmn" in x
    )

    for table in tables:

        dock = table.find(
            "i",
            class_="dockq"
        )

        if dock is None:
            continue

        data_url = dock.get(
            "data-url",
            ""
        )

        m = re.search(
            r"(\d{2}-\d{2}-\d{4})",
            data_url
        )

        if not m:
            continue

        draw_date = pd.to_datetime(
            m.group(1),
            format="%d-%m-%Y"
        )

        rows = table.find_all("tr")

        for row in rows[1:]:

            cells = row.find_all("td")

            if len(cells) < 2:
                continue

            for cell in cells[1:]:

                numbers = re.findall(
                    r"\d+",
                    cell.get_text(
                        "\n",
                        strip=True
                    )
                )

                for number in numbers:

                    records.append([
                        draw_date,
                        region,
                        number
                    ])

    return pd.DataFrame(
        records,
        columns=[
            "Date",
            "Region",
            "Number"
        ]
    )

# ==================================================
# LOAD DATA
# ==================================================

def load_data():

    print("Loading MB...")
    df_mb = scrape_mb()

    print("Loading MT...")
    df_mt = scrape_mtmn(
        URL_MT,
        "MT"
    )

    print("Loading MN...")
    df_mn = scrape_mtmn(
        URL_MN,
        "MN"
    )

    df = pd.concat(
        [
            df_mb,
            df_mt,
            df_mn
        ],
        ignore_index=True
    )

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    df["Number"] = (
        df["Number"]
        .astype(str)
    )

    df = (
        df
        .dropna()
        .drop_duplicates()
        .sort_values(
            [
                "Date",
                "Region"
            ]
        )
        .reset_index(drop=True)
    )

    print(
        "Rows:",
        len(df)
    )

    print(
        "Dates:",
        df["Date"].nunique()
    )

    return df

# ==================================================
# PREPARE
# ==================================================

def prepare_data(df):

    df = df.copy()

    df["Number2D"] = (
        df["Number"]
        .astype(str)
        .str[-2:]
        .str.zfill(2)
    )

    df["Number3D"] = (
        df["Number"]
        .astype(str)
        .str[-3:]
        .str.zfill(3)
    )

    df["Head"] = (
        df["Number3D"]
        .str[0]
    )

    return df

# ==================================================
# OUTPUT 1
# TOP 10 SO CHUA RA
# ==================================================

def build_missing_report(df):

    today = (
        df["Date"]
        .max()
        .normalize()
    )

    all_2d = [
        f"{i:02}"
        for i in range(100)
    ]

    result = []

    for num in all_2d:

        temp = df[
            df["Number2D"] == num
        ].copy()

        if temp.empty:

            last_date = pd.NaT

            last_region = ""

            missing_days = 9999

        else:

            last_date = (
                temp["Date"]
                .max()
            )

            last_regions = (
                temp[
                    temp["Date"]
                    == last_date
                ]["Region"]
                .drop_duplicates()
                .sort_values()
                .tolist()
            )

            last_region = ",".join(
                last_regions
            )

            missing_days = (
                today
                -
                last_date.normalize()
            ).days

        result.append([
            num,
            last_date,
            last_region,
            missing_days
        ])

    df_missing = pd.DataFrame(
        result,
        columns=[
            "Number2D",
            "LastDate",
            "LastRegion",
            "MissingDays"
        ]
    )

    df_missing = (
        df_missing
        .sort_values(
            "MissingDays",
            ascending=False
        )
        .reset_index(drop=True)
    )

    df_missing.insert(
        0,
        "Rank",
        range(
            1,
            len(df_missing) + 1
        )
    )

    df_missing = (
        df_missing
        .head(10)
    )

    return df_missing

# ==================================================
# HEAD ANALYSIS
# ==================================================

def build_head_table(
    df_source,
    region_name
):

    today = (
        df_source["Date"]
        .max()
        .normalize()
    )

    weekday_today = (
        today.dayofweek
    )

    region_df = df_source[
        df_source["Region"]
        == region_name
    ].copy()

    # Các kỳ cùng thứ hiện tại
    same_day_df = region_df[
        region_df["Date"].dt.dayofweek
        == weekday_today
    ]

    last_7_days = (
        today
        - pd.Timedelta(days=6)
    )

    last_14_days = (
        today
        - pd.Timedelta(days=13)
    )

    last_30_days = (
        today
        - pd.Timedelta(days=29)
    )

    rows = []

    for head in map(str, range(10)):

        temp_all = region_df[
            region_df["Head"] == head
        ]

        temp_same_day = same_day_df[
            same_day_df["Head"] == head
        ]

        count_7d = temp_all[
            temp_all["Date"] >= last_7_days
        ].shape[0]

        count_14d = temp_all[
            temp_all["Date"] >= last_14_days
        ].shape[0]

        count_30d = temp_all[
            temp_all["Date"] >= last_30_days
        ].shape[0]

        same_day_count = (
            temp_same_day.shape[0]
        )

        total_count = (
            temp_all.shape[0]
        )

        rows.append([
            head,
            count_7d,
            count_14d,
            count_30d,
            same_day_count,
            total_count
        ])

    result = pd.DataFrame(
        rows,
        columns=[
            "Head",
            "Count7D",
            "Count14D",
            "Count30D",
            "SameDay",
            "TotalCount"
        ]
    )

    # Giữ đúng thứ tự 0 -> 9
    result["Head"] = result["Head"].astype(int)

    result = (
        result
        .sort_values("Head")
        .reset_index(drop=True)
    )

    result.insert(
        0,
        "Rank",
        range(
            1,
            len(result) + 1
        )
    )

    return result

# ==================================================
# TELEGRAM MESSAGE
# ==================================================

def build_message(
    df_missing,
    df_head_mb,
    df_head_mt,
    df_head_mn
):

    msg = ""

    msg += (
        "🎯 2P REPORT\n\n"
    )

    msg += (
        "TOP 10 SO CHUA RA\n\n"
    )

    for _, row in df_missing.iterrows():

        msg += (
            f"{row['Number2D']} | "
            f"{row['MissingDays']} ngay | "
            f"{row['LastRegion']}\n"
        )

    msg += "\n"

    for region_name, region_df in [

        ("MB", df_head_mb),
        ("MT", df_head_mt),
        ("MN", df_head_mn)

    ]:

        msg += (
            f"\n===== {region_name} =====\n"
        )

        for _, row in region_df.iterrows():

            msg += (
                f"Dau {row['Head']} | "
                f"7D:{row['Count7D']} | "
                f"14D:{row['Count14D']} | "
                f"30D:{row['Count30D']} | "
                f"SameDay:{row['SameDay']}\n"
            )

    return msg
# ==================================================
# MAIN
# ==================================================

def main():

    print(
        "Loading data..."
    )

    df = load_data()

    df = prepare_data(df)

    print(
        "Building Missing Report..."
    )

    df_top10_missing = (
        build_missing_report(df)
    )

    print(
        "Building MB..."
    )

    df_head_mb = (
        build_head_table(
            df,
            "MB"
        )
    )

    print(
        "Building MT..."
    )

    df_head_mt = (
        build_head_table(
            df,
            "MT"
        )
    )

    print(
        "Building MN..."
    )

    df_head_mn = (
        build_head_table(
            df,
            "MN"
        )
    )

    msg = build_message(
        df_top10_missing,
        df_head_mb,
        df_head_mt,
        df_head_mn
    )

    print(msg)

    send_telegram(msg)

    print(
        "Completed."
    )

# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    main()
