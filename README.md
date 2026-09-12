# ريل جلسة التخاطب — Speech Therapy Session Reel

مونتاج احترافي لفيديو جلسة تخاطب (تدريب الحلقات الملوّنة)، جاهز للنشر على فيسبوك كـ Reel.

**الناتج:** `output/reel_facebook.mp4` — ‏1080×1920، ‏30fps، ‏47.8 ثانية، ‏H.264 + AAC.

## اللي اتعمل في المونتاج

| | |
|---|---|
| المقاس | ‏1080×1920 (‏9:16) — مقاس ريلز فيسبوك بالظبط |
| الكابشن | عربي على الشاشة، ‏8 جمل متزامنة مع كل خطوة في الجلسة |
| العنوان | تتر افتتاحي متحرك فوق الفيديو نفسه (مش كارت ساكت) |
| المزيكا | موسيقى هادية للأطفال، متعملة مخصوص للفيديو ده |
| النهاية | كارت ختامي مع كول-تو-أكشن + انتقال ناعم (dissolve) |
| شريط التقدّم | خط رفيع تحت الكابشن بيوضّح فاضل قد إيه |
| تصحيح الألوان | رفع الكونتراست والتشبّع وزيادة الحدة بعد التكبير |
| الإيقاع | تسريع خفيف ‏1.15× يشدّ الإيقاع من غير ما يبان مسرّع |
| الصوت | ‏-13.8 LUFS و ‏-1.5 dBFS — مطابق لمعيار فيسبوك |

### نقطتان مهمتان

**الفيديو الأصلي مالهوش صوت خالص** (مفيش audio stream). فالمزيكا هي كل الصوت في الريل، وعشان كده الكابشن هو اللي بيشيل الرسالة كلها.

**المزيكا متولّدة من الصفر** بكود بايثون (سلّم خماسي في دو ماجور، ‏72 نبضة/دقيقة، صوت علبة موسيقى مع خلفية ناعمة). يعني مفيش أي حقوق ملكية عليها، ومش هتتفلتر من نظام حقوق النشر بتاع فيسبوك — وده اللي بيوقّع معظم الريلز.

## الكابشن الجاهز للنشر على فيسبوك

> اللعب مش مجرد تسلية… ده أقوى وسيلة تعليم للطفل 🌈
>
> في التدريب ده بنشتغل على أكتر من مهارة في نفس الوقت:
> • تسمية الألوان والتعرّف عليها
> • ترتيب الأحجام من الأكبر للأصغر
> • تنفيذ التعليمات خطوة بخطوة
> • تقوية العضلات الدقيقة للأصابع
> • الانتظار والتبادل (دوري… ودورك)
>
> كل طفل له إيقاعه الخاص، والصبر والتكرار سرّ التقدّم 💛
>
> احفظوا الفيديو وشاركوه مع أم محتاجة تشوفه.
>
> #تخاطب #تأخر_الكلام #تنمية_مهارات #جلسات_تخاطب #أطفال #النطق_والتخاطب
> #تخاطب_أطفال #مهارات_حركية #توحد #تربية

## قبل النشر

- اتأكدي إن عندك **موافقة ولي الأمر** على نشر فيديو فيه الطفل.
- لو عايزة تخفي هوية الطفل أكتر، ممكن نضيف بلور على الوش — قوليلي وأعملها.
- أفضل وقت نشر لمحتوى الأمهات: من ٨ لـ ١١ مساءً بتوقيت القاهرة.

---

## إعادة البناء / التعديل — Rebuilding

```bash
./scripts/build_reel.sh [SOURCE] [OUTPUT]
```

Requires `ffmpeg` (with libass built against HarfBuzz and FriBidi) and the
`fonts-lemonada` package. No Python dependencies beyond the standard library.

### Files

- `scripts/build_reel.sh` — the whole pipeline; grade, speed, captions, end card, mix, encode.
- `scripts/gen_subs.py` — writes the burned-in caption tracks (`main.ass`, `outro.ass`).
- `scripts/make_music.py` — synthesises the background track.
- `build/source.mov` — the original footage.

### Editing the on-screen captions

Caption text and timings live in the `CAPTIONS` list in `scripts/gen_subs.py`,
as `(start, end, line1, line2)`. Titles are `TITLE_MAIN` / `TITLE_SUB`, and the
end card is `OUTRO_LINES` / `OUTRO_CTA`. Re-run `build_reel.sh` after editing.

Keep every ASS style's `Spacing` at `0`. A non-zero value makes libass lay out
glyphs individually, which silently disables Arabic shaping and bidi — the text
renders backwards in disconnected letterforms.

### Tuning

Knobs at the top of `build_reel.sh`: `SPEED` (pacing), `OUTRO` (end card
length), `XFADE` (dissolve), and `GRADE` (the colour correction string).

To add a clinic name or handle to the reel, add a persistent `Dialogue` line to
the header of `build_main()` in `gen_subs.py`.
