from main import (
    load_data,
    build_scrape_status_message,
    send_telegram
)

def main():

    print(
        "Loading data..."
    )

    (
        df,
        df_mb,
        df_mt,
        df_mn
    ) = load_data()

    print(
        "Building scrape status..."
    )
  
    msg = build_scrape_status_message(
        df_mb,
        df_mt,
        df_mn
    )

    print(msg)
  
    send_telegram(
        msg
    )
  
    print(
        "Completed."
    )


if __name__ == "__main__":

    main()
