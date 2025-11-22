import flet as ft
import sqlite3
import base64
import os
import shutil # APK ke liye ye zaroori hai

# ================= CONFIGURATION =================
DB_FILENAME = "Ward11_Only.db"

# --- APK PATH LOGIC (Jugaad for Android) ---
def get_db_path():
    """Android aur PC dono ke liye sahi path nikalta hai"""
    try:
        # Mobile storage path (App Data Directory)
        return os.path.join(os.getcwd(), DB_FILENAME)
    except:
        return DB_FILENAME

DB_PATH = get_db_path()

def configure_mobile_db():
    """Agar DB phone ki memory me nahi hai, to assets se copy karo"""
    if not os.path.exists(DB_PATH):
        # Assets folder se original DB uthao
        # Flet APK me assets root folder ke relative hote hain
        asset_db_path = os.path.join("assets", DB_FILENAME)
        
        # Agar assets me file hai to copy karo
        if os.path.exists(asset_db_path):
            try:
                shutil.copy(asset_db_path, DB_PATH)
                print("✅ Database copied to internal storage!")
            except Exception as e:
                print(f"❌ Error copying DB: {e}")
        else:
            # Fallback for PC testing if file is in root
            if os.path.exists(DB_FILENAME):
                print("ℹ️ PC Mode: Using local DB")
            else:
                print("⚠️ Warning: Database not found anywhere.")

# Call this function BEFORE anything else
configure_mobile_db()

# ================= DATABASE HELPERS =================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY,
            header_path TEXT,
            cand_name TEXT,
            cand_party TEXT,
            cand_symbol TEXT
        )
    """)
    cursor.execute("SELECT count(*) FROM app_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO app_settings (id, header_path, cand_name, cand_party, cand_symbol) VALUES (1, '', '', '', '')")
    conn.commit()
    conn.close()

def save_settings_to_db(header, name, party, symbol):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE app_settings 
        SET header_path=?, cand_name=?, cand_party=?, cand_symbol=? 
        WHERE id=1
    """, (header, name, party, symbol))
    conn.commit()
    conn.close()

def load_settings_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT header_path, cand_name, cand_party, cand_symbol FROM app_settings WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    return row if row else ("", "", "", "")

def get_voter_data(query):
    if not os.path.exists(DB_PATH): return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Index Map: 0=srno, 1=vcardid, 2=name, 3=age, 4=sex, 5=booth, 6=part_no, 7=assembly_mapping, 8=address
        sql = f"""
        SELECT srno, vcardid, l_voter_name, age, sex, l_boothaddress, 
               part_no, assembly_mapping, l_address
        FROM voters 
        WHERE vcardid = '{query}' 
           OR l_voter_name LIKE '%{query}%' 
           OR e_voter_name LIKE '%{query}%'
        LIMIT 10
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"DB Error: {e}")
        return []

def get_image_base64(path):
    # APK Logic: Check assets folder if path not found
    if not os.path.exists(path):
        # Try finding in assets
        asset_path = os.path.join("assets", os.path.basename(path))
        if os.path.exists(asset_path):
            path = asset_path
            
    if path and os.path.exists(path):
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    return ""

# ================= MAIN APP UI =================
def main(page: ft.Page):
    page.title = "Rajyog Election Print"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.padding = 10
    page.bgcolor = ft.Colors.GREY_100
    
    init_db()

    saved_header_path, saved_cand, saved_party, saved_symbol = load_settings_from_db()
    
    header_img_path = ft.Ref[str]()
    header_img_path.current = saved_header_path

    # --- UI Controls ---
    txt_cand_name = ft.TextField(label="उमेदवार (Candidate Name)", value=saved_cand)
    txt_party = ft.TextField(label="पार्टी (Party)", value=saved_party)
    txt_symbol = ft.TextField(label="निशाणी (Symbol)", value=saved_symbol)
    txt_header_status = ft.Text(value="Image Selected" if saved_header_path else "No Image", color=ft.Colors.GREEN if saved_header_path else ft.Colors.RED)
    
    search_box = ft.TextField(label="नाव किंवा EPIC नंबर टाका...", expand=True)

    # --- 1. PRINTING LOGIC (HTML - FINAL LAYOUT) ---
    def print_slip_action(voter):
        c_name = txt_cand_name.value
        c_party = txt_party.value
        c_sym = txt_symbol.value
        h_path = header_img_path.current

        img_b64 = get_image_base64(h_path)
        img_html = f'<img src="data:image/png;base64,{img_b64}" class="header-img">' if img_b64 else ""
        gender = "M" if voter[4] == "M" else "F" if voter[4] == "F" else str(voter[4])
        
        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: sans-serif; margin: 0; padding: 0; width: 100%; background-color: #fff; }}
                .container {{ padding: 2px; text-align: center; }}
                
                .header-img {{ 
                    display: block; 
                    margin-left: auto; 
                    margin-right: auto; 
                    width: 98%; 
                    max-height: 150px; 
                    object-fit: contain; 
                }}
                
                .cand-box {{ 
                    border: 2px solid #000; 
                    border-radius: 6px; 
                    padding: 5px; 
                    font-weight: bold; 
                    font-size: 14px; 
                    margin: 5px 2px; 
                    text-align: center; 
                }}
                
                .cut-line {{ margin: 5px 0; border-bottom: 2px dashed black; text-align: center; height: 10px; line-height: 20px; font-size: 16px; }}
                
                .voter-info {{ text-align: left; margin-top: 0px; font-size: 16px; padding: 0 5px; }}
                .bold {{ font-weight: bold; font-size: 18px; }}
                
                p {{ margin: 2px 0; }} 
                
                .row-compact {{ 
                    display: flex; 
                    justify-content: flex-start; 
                    gap: 30px; 
                    margin: 0; padding: 0;
                }}
                
                .epic-simple {{
                    font-size: 18px;
                    font-weight: bold;
                    margin: 5px 0;
                }}
                
                .polling-station {{
                    font-size: 18px; 
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div style="text-align: center;">{img_html}</div>

                <div class="cand-box">
                    उमेदवार : {c_name}<br>
                    पार्टी : {c_party}<br>
                    निशाणी : {c_sym}
                </div>

                <div class="cut-line">✂ ------------------------- ✂</div>

                <div class="voter-info">
                    <p class="bold">नाव - {voter[2]}</p>
                    
                    <div class="row-compact">
                        <span>प्रभाग : <b>{voter[6]}</b></span>
                        <span>अ क्र : <b>{voter[0]}</b></span>
                    </div>
                    
                    <div class="row-compact">
                        <span>वय : {voter[3]}</span>
                        <span>लिंग : {gender}</span>
                    </div>

                    <div class="epic-simple">
                         मतदान कार्ड : {voter[1]}
                    </div>

                    <p>विधानसभा क्र : {voter[7]}</p>
                    <p>पत्ता :- {voter[8]}</p>

                    <div style="margin-top: 8px;">
                        <span class="bold">मतदान केंद्र : </span><br>
                        <span class="polling-station">{voter[5]}</span>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 10px; font-size: 10px;">
                    Powered by Rajyog Election App
                </div>
            </div>
        </body>
        </html>
        """
        html_b64 = base64.b64encode(html.encode('utf-8')).decode('utf-8')
        page.launch_url(f"rawbt:data:text/html;base64,{html_b64}")

    # --- 2. PREVIEW LOGIC (FINAL UI) ---
    def show_preview(e, voter):
        try:
            c_name = txt_cand_name.value
            c_party = txt_party.value
            c_sym = txt_symbol.value
            h_path = header_img_path.current
            img_b64 = get_image_base64(h_path)
            
            v_name = str(voter[2]) if voter[2] else ""
            v_part = str(voter[6]) if voter[6] else ""
            v_srno = str(voter[0]) if voter[0] else ""
            v_epic = str(voter[1]) if voter[1] else ""
            v_addr = str(voter[8]) if voter[8] else ""
            v_age = str(voter[3]) if voter[3] else ""
            v_booth = str(voter[5]) if voter[5] else ""
            v_assembly = str(voter[7]) if voter[7] else ""
            
            gender_raw = voter[4]
            gender = "M" if gender_raw == "M" else "F" if gender_raw == "F" else str(gender_raw)

            preview_content = ft.Container(
                bgcolor=ft.Colors.WHITE,
                padding=15,
                border_radius=10,
                content=ft.Column([
                    
                    # Header
                    ft.Container(
                        content=ft.Image(src_base64=img_b64, fit=ft.ImageFit.CONTAIN, height=100) if img_b64 else ft.Text("NO HEADER IMAGE", color="red"),
                        alignment=ft.alignment.center,
                        width=320
                    ),
                    
                    # Candidate Box
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"उमेदवार : {c_name}", weight="bold", text_align="center", size=14, color="black"),
                            ft.Text(f"पार्टी : {c_party}", weight="bold", text_align="center", size=14, color="black"),
                            ft.Text(f"निशाणी : {c_sym}", weight="bold", text_align="center", size=14, color="black"),
                        ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
                        border=ft.border.all(2, ft.Colors.BLACK),
                        border_radius=8,
                        padding=10,
                        margin=ft.margin.symmetric(vertical=10),
                        alignment=ft.alignment.center,
                        bgcolor=ft.Colors.WHITE
                    ),

                    # Cut Line
                    ft.Row([
                        ft.Icon(ft.Icons.CUT, size=16, color="black"), 
                        ft.Text("- - - - - - - - - - - - - -", color="black"), 
                        ft.Icon(ft.Icons.CUT, size=16, color="black")
                    ], alignment=ft.MainAxisAlignment.CENTER),

                    # Voter Info
                    ft.Text(f"नाव - {v_name}", size=18, weight="bold", color="black"),
                    
                    ft.Row([
                         ft.Text(f"प्रभाग : {v_part}", weight="bold", color="black", size=15),
                         ft.Container(width=30), 
                         ft.Text(f"अ क्र : {v_srno}", weight="bold", color="black", size=15),
                    ], alignment=ft.MainAxisAlignment.START, spacing=0),
                    
                    ft.Row([
                         ft.Text(f"वय : {v_age}", color="black"),
                         ft.Container(width=50), 
                         ft.Text(f"लिंग : {gender}", color="black"),
                    ], alignment=ft.MainAxisAlignment.START, spacing=0),
                    
                    ft.Text(f"मतदान कार्ड (EPIC) : {v_epic}", weight="bold", size=16, color="black"),
                    
                    ft.Text(f"विधानसभा क्र : {v_assembly}", color="black"),
                    ft.Text(f"पत्ता :- {v_addr}", size=13, color="black"),
                    
                    ft.Container(height=10),
                    
                    ft.Text("मतदान केंद्र :", weight="bold", color="black", size=16),
                    ft.Text(f"{v_booth}", size=18, weight="bold", color="black"),

                ], width=320, scroll=ft.ScrollMode.AUTO, spacing=2)
            )

            dlg_preview = ft.AlertDialog(
                title=ft.Text("Slip Preview", text_align="center"),
                content=ft.Container(
                    content=preview_content, 
                    height=500, 
                    padding=0,
                    bgcolor=ft.Colors.TRANSPARENT
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda e: page.close(dlg_preview)),
                    ft.ElevatedButton("PRINT 🖨️", bgcolor=ft.Colors.GREEN, color="white", on_click=lambda e: print_slip_action(voter))
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER,
                bgcolor=ft.Colors.WHITE 
            )
            page.open(dlg_preview)
            
        except Exception as ex:
            print(f"Preview Error: {ex}")
            page.snack_bar = ft.SnackBar(ft.Text(f"Preview Error: {ex}"))
            page.snack_bar.open = True
            page.update()

    # --- Search UI ---
    results_col = ft.Column(scroll=ft.ScrollMode.AUTO)

    def do_search(query):
        results_col.controls.clear()
        if not query: return
        
        data = get_voter_data(query)
        if not data:
            results_col.controls.append(ft.Text("डेटा सापडला नाही!", color=ft.Colors.RED))
        else:
            for row in data:
                card = ft.Card(
                    content=ft.Container(
                        padding=10,
                        bgcolor=ft.Colors.WHITE,
                        border_radius=10,
                        content=ft.Column([
                            ft.Text(f"{row[2]}", size=16, weight="bold", color="black"),
                            ft.Row([
                                ft.Text(f"EPIC: {row[1]}", color="black"),
                                ft.Text(f"Sr.No: {row[0]}", color="black")
                            ]),
                            ft.Text(f"पत्ता: {row[8]}", size=12, color="grey"),
                            ft.Divider(),
                            ft.Row([
                                ft.OutlinedButton("View Slip 👁️", on_click=lambda e, r=row: show_preview(e, r), style=ft.ButtonStyle(color=ft.Colors.BLUE)),
                                ft.ElevatedButton("Print 🖨️", on_click=lambda e, r=row: print_slip_action(r), bgcolor=ft.Colors.GREEN, color="white")
                            ], alignment=ft.MainAxisAlignment.END)
                        ])
                    )
                )
                results_col.controls.append(card)
        page.update()

    def on_search_click(e):
        do_search(search_box.value)

    # --- Settings & Files ---
    def pick_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            path = e.files[0].path
            header_img_path.current = path
            txt_header_status.value = f"Selected: {os.path.basename(path)}"
            txt_header_status.color = ft.Colors.GREEN
            page.update()

    file_picker = ft.FilePicker(on_result=pick_file_result)
    page.overlay.append(file_picker)

    def save_settings_click(e):
        save_settings_to_db(header_img_path.current, txt_cand_name.value, txt_party.value, txt_symbol.value)
        page.snack_bar = ft.SnackBar(ft.Text("Settings Saved Successfully!"))
        page.snack_bar.open = True
        page.update()

    def connect_printer(e):
        page.launch_url("rawbt:")

    # --- Layout ---
    settings_container = ft.Column([
        ft.Text("Candidate Setup", size=16, weight="bold"),
        ft.ElevatedButton("Select Header Image", icon=ft.Icons.IMAGE, on_click=lambda _: file_picker.pick_files(allow_multiple=False)),
        txt_header_status,
        txt_cand_name,
        txt_party,
        txt_symbol,
        ft.ElevatedButton("Save Settings", on_click=save_settings_click, bgcolor="blue", color="white")
    ], visible=False)

    def show_settings_drawer(e):
        settings_container.visible = not settings_container.visible
        page.update()

    top_bar = ft.Row([
        ft.IconButton(ft.Icons.BLUETOOTH_CONNECTED, icon_color="blue", tooltip="Connect Printer", on_click=connect_printer),
        ft.Text("Voter Slip", size=20, weight="bold"),
        ft.IconButton(ft.Icons.SETTINGS, tooltip="Settings", on_click=lambda e: show_settings_drawer(e))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    search_row = ft.Row([
        search_box,
        ft.IconButton(ft.Icons.SEARCH, icon_size=30, on_click=on_search_click, icon_color="green")
    ])

    page.add(
        top_bar,
        ft.Divider(),
        settings_container, 
        ft.Divider(),
        search_row,
        results_col
    )

if __name__ == "__main__":
    ft.app(target=main)