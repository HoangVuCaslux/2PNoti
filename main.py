import os
import re
import requests
import pandas as pd

from bs4 import BeautifulSoup
from datetime import timedelta

# ==================================================
# CONFIG
# ==================================================

REPORT_TYPE = os.getenv(
    "REPORT_TYPE",
    "MB"
)

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
            "text": message,
            "parse_mode": "HTML"
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
# TOP 10 
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

    return df_missing

# ==================================================
# HEAD ANALYSIS
# ==================================================

def build_head_table(
    df_source,
    region_name
):

    # Ngày dữ liệu mới nhất
    dataset_date = (
        df_source["Date"]
        .max()
        .normalize()
    )

    # Ngày hiện tại (dùng để xác định SameDay)
    today = (
        pd.Timestamp.now()
        .normalize()
    )

    # Thứ đang dùng để tính SameDay
    weekday_today = (
        today.dayofweek
    )

    # Chỉ lấy dữ liệu của miền
    region_df = df_source[
        (df_source["Region"] == region_name)
        &
        (
            df_source["Number"]
            .astype(str)
            .str.len()
            >= 3
        )
    ].copy()

    # Các khoảng thời gian vẫn tính theo dataset
    last_7_days = (
        dataset_date
        - pd.Timedelta(days=6)
    )

    last_14_days = (
        dataset_date
        - pd.Timedelta(days=13)
    )

    last_30_days = (
        dataset_date
        - pd.Timedelta(days=29)
    )

    # SameDay tính theo thứ của ngày hiện tại
    same_day_df = region_df[
        region_df["Date"].dt.dayofweek
        == weekday_today
    ]

    same_day_14d = same_day_df[
        same_day_df["Date"] >= last_14_days
    ]

    same_day_30d = same_day_df[
        same_day_df["Date"] >= last_30_days
    ]

    rows = []

    for head in map(str, range(10)):

        temp_all = region_df[
            region_df["Head"] == head
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

        sd14 = same_day_14d[
            same_day_14d["Head"] == head
        ].shape[0]

        sd30 = same_day_30d[
            same_day_30d["Head"] == head
        ].shape[0]

        sdall = same_day_df[
            same_day_df["Head"] == head
        ].shape[0]

        total_count = (
            temp_all.shape[0]
        )

        rows.append([
            head,
            count_7d,
            count_14d,
            count_30d,
            sd14,
            sd30,
            sdall,
            total_count
        ])

    result = pd.DataFrame(
        rows,
        columns=[
            "Head",
            "Count7D",
            "Count14D",
            "Count30D",
            "SameDay14D",
            "SameDay30D",
            "SameDayAll",
            "TotalCount"
        ]
    )

    result["Head"] = (
        result["Head"]
        .astype(int)
    )

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
            len(result)+1
        )
    )

    return (
        result,
        dataset_date,
        weekday_today
    )
    
# ==================================================
# PAIR ANALYSIS
# ==================================================

def build_pair_analysis(
    df,
    df_top10_missing,
    region_name
):

    region_df = df[
        (df["Region"] == region_name)
        &
        (
            df["Number"]
            .astype(str)
            .str.len()
            >= 3
        )
    ].copy()

    dataset_date = (
        region_df["Date"]
        .max()
        .normalize()
    )
    
    today = (
        pd.Timestamp.now()
        .normalize()
    )
    
    last_14_days = (
        dataset_date
        - pd.Timedelta(days=13)
    )
    
    last_30_days = (
        dataset_date
        - pd.Timedelta(days=29)
    )
    
    weekday_today = (
        today.dayofweek
    )
    
    same_day_df = region_df[
        region_df["Date"]
        .dt.dayofweek
        ==
        weekday_today
    ]
    
    same_day_14d = same_day_df[
        same_day_df["Date"]
        >= last_14_days
    ]
    
    same_day_30d = same_day_df[
        same_day_df["Date"]
        >= last_30_days
    ]    

    result_text = ""

    target_numbers = (
        df_top10_missing["Number2D"]
        .tolist()
    )

    for number2d in target_numbers:

        last_digit = number2d[-1]

        result_text += (
            f"\n🎯 So {number2d}\n\n"
        )

        result_text += (
            f"Các đầu số thường ra với đuôi {last_digit}\n\n"
        )

        # -----------------------------
        # Đầu số đi với đuôi cuối
        # -----------------------------

        for head in map(str, range(10)):

            temp14 = region_df[
                (region_df["Number3D"].str[0] == head)
                &
                (region_df["Number3D"].str[-1] == last_digit)
                &
                (region_df["Date"] >= last_14_days)
            ]

            temp30 = region_df[
                (region_df["Number3D"].str[0] == head)
                &
                (region_df["Number3D"].str[-1] == last_digit)
                &
                (region_df["Date"] >= last_30_days)
            ]

            same_day_14_count = same_day_14d[
                (same_day_14d["Number3D"].str[0] == head)
                &
                (same_day_14d["Number3D"].str[-1] == last_digit)
            ].shape[0]
            
            same_day_30_count = same_day_30d[
                (same_day_30d["Number3D"].str[0] == head)
                &
                (same_day_30d["Number3D"].str[-1] == last_digit)
            ].shape[0]
            
            same_day_all_count = same_day_df[
                (same_day_df["Number3D"].str[0] == head)
                &
                (same_day_df["Number3D"].str[-1] == last_digit)
            ].shape[0]
            
            result_text += (
                f"🔹 Dau {head}\n"
            )
            
            result_text += (
                f"| {'14D:'+str(len(temp14)):<10}"
                f"| {'30D:'+str(len(temp30)):<10}|\n"
            )
            
            result_text += (
                f"| {'SD14:'+str(same_day_14_count):<10}"
                f"| {'SD30:'+str(same_day_30_count):<10}"
                f"| {'SDAll:'+str(same_day_all_count):<10}|\n\n"
            )

        # -----------------------------
        # Đầu số đi với chính cặp số
        # -----------------------------

        result_text += (
            f"\nCác đầu số thường ra với {number2d}\n\n"
        )

        for head in map(str, range(10)):

            target_3d = (
                head +
                number2d
            )

            count_all = (
                region_df[
                    region_df["Number3D"]
                    ==
                    target_3d
                ]
                .shape[0]
            )
            
            count_sd14 = (
                same_day_14d[
                    same_day_14d["Number3D"]
                    ==
                    target_3d
                ]
                .shape[0]
            )
            
            count_sd30 = (
                same_day_30d[
                    same_day_30d["Number3D"]
                    ==
                    target_3d
                ]
                .shape[0]
            )
            
            count_sdall = (
                same_day_df[
                    same_day_df["Number3D"]
                    ==
                    target_3d
                ]
                .shape[0]
            )
            
            result_text += (
                f"🔹 Dau {head}\n"
            )
            
            result_text += (
                f"| {'All:'+str(count_all):<10}|\n"
            )
            
            result_text += (
                f"| {'SD14:'+str(count_sd14):<10}"
                f"| {'SD30:'+str(count_sd30):<10}"
                f"| {'SDAll:'+str(count_sdall):<10}|\n\n"
            )

    return result_text
    
# ==================================================
# HEAD ANALYSIS MESSAGE
# ==================================================

def build_head_message(
    region_name,
    region_df,
    dataset_date,
    weekday_today
):

    msg = ""

    weekday_name = {
        0: "Thứ 2",
        1: "Thứ 3",
        2: "Thứ 4",
        3: "Thứ 5",
        4: "Thứ 6",
        5: "Thứ 7",
        6: "Chủ Nhật"
    }[
        weekday_today
    ]    
        
    msg += (
        f"📊 {region_name} ANALYSIS\n\n"
        f"📅 Dữ liệu mới nhất vào : {dataset_date:%d/%m/%Y}\n"
        f"📆 Ngày so sánh : {weekday_name}\n\n"
    )

    msg += (
        "TẦN SUẤT RA CỦA CÁC ĐẦU SỐ\n\n"
    )

    for _, row in region_df.iterrows():

        msg += (
            f"🔹 Dau {row['Head']}\n"
        )

        msg += "<pre>\n"

        msg += (
            f"| {'7D:'+str(row['Count7D']):<10}"
            f"| {'14D:'+str(row['Count14D']):<10}"
            f"| {'30D:'+str(row['Count30D']):<10}|\n"
        )

        msg += (
            f"| {'SD14:'+str(row['SameDay14D']):<10}"
            f"| {'SD30:'+str(row['SameDay30D']):<10}"
            f"| {'SDAll:'+str(row['SameDayAll']):<10}|\n"
        )

        msg += "</pre>\n\n"

    return msg

# ==================================================
# PAIR ANALYSIS MESSAGES
# ==================================================

def build_pair_messages(
    df,
    df_missing,
    region_name
):

    messages = []

    top3_numbers = (
        df_missing["Number2D"]
        .head(3)
        .tolist()
    )

    for number2d in top3_numbers:

        temp_missing = pd.DataFrame(
            {
                "Number2D": [number2d]
            }
        )

        msg = ""

        msg += (
            f"🎯 {region_name} PAIR ANALYSIS\n\n"
        )

        msg += "<pre>\n"

        msg += build_pair_analysis(
            df,
            temp_missing,
            region_name
        )

        msg += "</pre>"

        messages.append(
            msg
        )

    return messages
    
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

    # ==================================
    # ALERT ONLY
    # Missing >= 3 days
    # ==================================

    df_top10_missing_alert = (
        df_top10_missing[
            df_top10_missing["MissingDays"] >= 3
        ]
        .reset_index(drop=True)
    )

    print(
        "Building MB..."
    )

    (
        df_head_mb,
        dataset_date_mb,
        weekday_mb
    ) = build_head_table(
        df,
        "MB"
    )
    
    (
        df_head_mt,
        dataset_date_mt,
        weekday_mt
    ) = build_head_table(
        df,
        "MT"
    )
    
    (
        df_head_mn,
        dataset_date_mn,
        weekday_mn
    ) = build_head_table(
        df,
        "MN"
    )

    # ==================================
    # REPORT INFO
    # ==================================
    
    if REPORT_TYPE == "MN":
    
        dataset_date = dataset_date_mn
        weekday_today = weekday_mn
    
    elif REPORT_TYPE == "MT":
    
        dataset_date = dataset_date_mt
        weekday_today = weekday_mt
    
    else:
    
        dataset_date = dataset_date_mb
        weekday_today = weekday_mb
    
    weekday_name = {
        0: "Thứ 2",
        1: "Thứ 3",
        2: "Thứ 4",
        3: "Thứ 5",
        4: "Thứ 6",
        5: "Thứ 7",
        6: "Chủ Nhật"
    }[weekday_today]
    
    # ==================================
    # NO ALERT
    # ==================================

    if df_top10_missing_alert.empty:

        print(
            "No number missing >= 3 days."
        )

        print(
            "Skip Telegram notification."
        )

        print(
            "Completed."
        )

        return

    # ==================================
    # MESSAGE 1
    # TOP 10 MISSING
    # ==================================

    msg_missing = (
        "🎯 MISSING NUMBER >= 3 DAYs\n\n"
        f"📅 Dữ liệu mới nhất vào : {dataset_date:%d/%m/%Y}\n"
        f"📆 Ngày so sánh : {weekday_name}\n\n"
    )

    for _, row in (
        df_top10_missing_alert
        .iterrows()
    ):

        msg_missing += (
            f"{row['Number2D']} | "
            f"{row['MissingDays']} ngay | "
            f"{row['LastRegion']}\n"
        )

    print(msg_missing)

    send_telegram(
        msg_missing
    )

    # ==================================
    # MESSAGE 2
    # HEAD ANALYSIS
    # ==================================
    
    if REPORT_TYPE == "MN":
    
        region_df = df_head_mn
    
    elif REPORT_TYPE == "MT":
    
        region_df = df_head_mt
    
    else:
    
        region_df = df_head_mb
    
    msg_head = build_head_message(
        REPORT_TYPE,
        region_df,
        dataset_date,
        weekday_today
    )
    
    print(
        f"REPORT_TYPE = {REPORT_TYPE}"
    )
    
    print(msg_head)
    
    send_telegram(
        msg_head
    )
    
    # ==================================
    # MESSAGE 3
    # PAIR ANALYSIS
    # ==================================
    
    pair_messages = build_pair_messages(
        df,
        df_top10_missing_alert,
        REPORT_TYPE
    )
    
    for msg_pair in pair_messages:
    
        print(msg_pair)
    
        send_telegram(
            msg_pair
        )
    
    print(
        "Completed."
    )

# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    main()
