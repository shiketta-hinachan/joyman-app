import base64
import io
import os
import random
from typing import List, Optional

import pandas as pd
import streamlit as st
from gtts import gTTS


########################################
# App Config
########################################
st.set_page_config(page_title="ジョイマン百人一首 読み上げ", page_icon="🎴", layout="centered")

TITLE = "ジョイマン百人一首 読み上げアプリ"
DEFAULT_XLSX = "ジョイマン百人一首_全リスト.xlsx"  # 同じフォルダに置くと自動で読み込みます
SHEET_NAME = "シート1"
COL_ID = "#"
COL_KAMI = "上の句"
COL_SHIMO = "下の句"


########################################
# Utilities
########################################
@st.cache_data(show_spinner=False)
def load_data(file_bytes: Optional[bytes]) -> pd.DataFrame:
    """アップロード/ローカルのExcelからデータフレームを作成"""
    if file_bytes is not None:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
    else:
        if not os.path.exists(DEFAULT_XLSX):
            raise FileNotFoundError(
                f"Excelが見つかりません。'{DEFAULT_XLSX}' をアプリと同じフォルダに置くか、画面からアップロードしてください。"
            )
        xls = pd.ExcelFile(DEFAULT_XLSX)

    df = pd.read_excel(xls, sheet_name=SHEET_NAME)
    # 必須カラム存在チェック
    for c in [COL_ID, COL_KAMI, COL_SHIMO]:
        if c not in df.columns:
            raise ValueError(f"Excelに必須カラムがありません: {c}")
    # 余分な空白/欠損を整形
    df[COL_KAMI] = df[COL_KAMI].astype(str).str.strip()
    df[COL_SHIMO] = df[COL_SHIMO].astype(str).str.strip()
    # IDをintに（念のため）
    df[COL_ID] = pd.to_numeric(df[COL_ID], errors="coerce").astype("Int64")
    df = df.dropna(subset=[COL_ID]).reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def tts_mp3_bytes(text: str, lang: str = "ja") -> bytes:
    """gTTSで日本語音声MP3を生成してbytesを返す（キャッシュ）"""
    tts = gTTS(text=text, lang=lang)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()


def audio_html(audio_bytes: bytes, autoplay: bool) -> str:
    """base64埋め込みのaudioタグを返す（autoplay制御つき）"""
    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    auto = "autoplay" if autoplay else ""
    # controlsは常に付与（ユーザーが停止/巻き戻しできるように）
    return f"""
    <audio controls {auto}>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mpeg">
        お使いのブラウザは audio 要素をサポートしていません。
    </audio>
    """


def pick_next_id(remaining: List[int]) -> Optional[int]:
    """未読IDからランダムに1つ選ぶ"""
    if not remaining:
        return None
    return random.choice(remaining)


########################################
# Session State 初期化
########################################
if "df" not in st.session_state:
    st.session_state.df = None

if "remaining_ids" not in st.session_state:
    st.session_state.remaining_ids: List[int] = []

if "current_id" not in st.session_state:
    st.session_state.current_id: Optional[int] = None

if "has_played_once" not in st.session_state:
    # 現在表示中の札について「自動読み上げ済みか？」
    st.session_state.has_played_once = False

if "manual_play_trigger" not in st.session_state:
    # ボタン押下による手動再生トリガー
    st.session_state.manual_play_trigger = False


########################################
# UI: Header / Uploader
########################################
st.title(TITLE)
st.caption("要件: 初回は自動で上の句を読み上げ。2回目以降はボタンで手動再生。下の句は表示のみ。未読重複なし。100枚完了で「完了」を表示。")

uploaded = st.file_uploader("Excelファイルをアップロード（未指定ならローカルのファイルを探します）", type=["xlsx"])

# データロード
try:
    st.session_state.df = load_data(uploaded.read() if uploaded is not None else None)
except Exception as e:
    st.error(str(e))
    st.stop()

df = st.session_state.df

# 初期化（初回のみ or 新しいファイルが入った時）
if not st.session_state.remaining_ids:
    all_ids = df[COL_ID].dropna().astype(int).tolist()
    st.session_state.remaining_ids = all_ids.copy()
    st.session_state.current_id = None
    st.session_state.has_played_once = False
    st.session_state.manual_play_trigger = False


########################################
# 全件消化チェック
########################################
if len(st.session_state.remaining_ids) == 0 and st.session_state.current_id is None:
    st.success("✅ 完了（100枚すべて読み上げました）")
    st.stop()


########################################
# 次の札を自動決定（初回 or 現在の札がない時）
########################################
if st.session_state.current_id is None:
    next_id = pick_next_id(st.session_state.remaining_ids)
    if next_id is None:
        st.success("✅ 完了（100枚すべて読み上げました）")
        st.stop()
    st.session_state.current_id = next_id
    # 未読リストから削除してロック
    st.session_state.remaining_ids.remove(next_id)
    # この札ではまだ自動読み上げしていない
    st.session_state.has_played_once = False
    st.session_state.manual_play_trigger = False

# 現在の札データ
row = df[df[COL_ID] == st.session_state.current_id].iloc[0]
kami = str(row[COL_KAMI])
shimo = str(row[COL_SHIMO])

########################################
# 進捗表示
########################################
total = df.shape[0]
read_count = total - len(st.session_state.remaining_ids)  # 現在表示中の札も既読カウントに含む
st.write(f"進捗: **{read_count}/{total}**")

########################################
# 表示（上の句・下の句）
########################################
st.markdown(
    f"""
    <div style="font-size: 1.6rem; line-height: 1.8; margin: 1rem 0;">
        <div style="opacity: 0.7;">札番号: {int(st.session_state.current_id)}</div>
        <div style="font-weight: 700; margin-top: 0.5rem;">上の句：{kami}</div>
    </div>
    """,
    unsafe_allow_html=True
)

########################################
# 音声（上の句のみ）
########################################
# 自動読み上げ（初回のみ）
if not st.session_state.has_played_once:
    try:
        audio_bytes = tts_mp3_bytes(kami, lang="ja")
        st.markdown(audio_html(audio_bytes, autoplay=True), unsafe_allow_html=True)
        st.session_state.has_played_once = True
    except Exception as e:
        st.error(f"音声合成に失敗しました: {e}")

# 手動読み上げボタン
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("もう一度読み上げ（上の句）", use_container_width=True):
        st.session_state.manual_play_trigger = True

with col2:
    go_next = st.button("次の札へ", use_container_width=True)

# 手動トリガー対応
if st.session_state.manual_play_trigger:
    try:
        audio_bytes = tts_mp3_bytes(kami, lang="ja")
        # ボタンクリックに応じて自動再生（= 手動起点の再生）
        st.markdown(audio_html(audio_bytes, autoplay=True), unsafe_allow_html=True)
    except Exception as e:
        st.error(f"音声合成に失敗しました: {e}")
    finally:
        st.session_state.manual_play_trigger = False

# 次の札へ
if go_next:
    # すべて読み終えた？
    if len(st.session_state.remaining_ids) == 0:
        # 現在の札をクリアして完了表示へ
        st.session_state.current_id = None
        st.rerun()
    else:
        next_id = pick_next_id(st.session_state.remaining_ids)
        st.session_state.current_id = next_id
        st.session_state.remaining_ids.remove(next_id)
        st.session_state.has_played_once = False
        st.session_state.manual_play_trigger = False
        st.rerun()


########################################
# フッター（注意書き）
########################################
with st.expander("下の句"):
    st.markdown(
    f"""
    <div style="font-size: 1.6rem; line-height: 1.8; margin: 1rem 0;">
        <div style="margin-top: 0.25rem;">下の句：{shimo}</div>
    </div>
    """,
    unsafe_allow_html=True
)
