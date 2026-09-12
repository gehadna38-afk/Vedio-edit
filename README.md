# ريل تنمية المهارات — Skills Development Reel

مونتاج احترافي لفيديو تدريب تنمية مهارات (لعبة الحلقات الملوّنة)، جاهز للنشر على فيسبوك كـ Reel.

**الناتج:** `output/reel_facebook.mp4` — ‏1080×1920، ‏30fps، ‏47.8 ثانية، ‏H.264 + AAC.

## اللي اتعمل في المونتاج

| | |
|---|---|
| المقاس | ‏1080×1920 (‏9:16) — مقاس ريلز فيسبوك بالظبط |
| الكابشن | عربي على الشاشة، ‏8 جمل متزامنة مع كل خطوة في التدريب |
| العنوان | تتر افتتاحي متحرك فوق الفيديو نفسه (مش كارت ساكت) |
| المزيكا | لحن أطفال مرِح بالزيلوفون والإيقاع الخفيف، متعمول مخصوص للفيديو ده |
| النهاية | كارت ختامي مع كول-تو-أكشن + انتقال ناعم (dissolve) |
| شريط التقدّم | خط رفيع تحت الكابشن بيوضّح فاضل قد إيه |
| الصورة | تنعيم خفيف للنويز قبل التكبير، وتصحيح ألوان وزيادة حدة بعده |
| الجودة | ‏CRF 17 / preset slower — ماستر نضيف قبل ما فيسبوك يعيد ضغطه |
| الإيقاع | تسريع خفيف ‏1.15× يشدّ الإيقاع من غير ما يبان مسرّع |
| الصوت | ‏-14.4 LUFS و ‏-1.3 dBFS — مطابق لمعيار فيسبوك |

### نقطتان مهمتان

**الفيديو الأصلي مالهوش صوت خالص** (مفيش audio stream). عشان كده الكابشن بيوصف **اللي ظاهر في الصورة بس** — مفيش أي جملة بتدّعي حاجة اتقالت في التدريب، لأن مفيش طريقة نتأكد منها.

**المزيكا متولّدة من الصفر** بكود بايثون: لحن أطفال من ٨ مازورات في دو ماجور، ‏104 نبضة/دقيقة، زيلوفون كميلودي فوق باص ماريمبا نطّاط مع كيك وشيكر خفيفين. يعني مفيش أي حقوق ملكية عليها، ومش هتتفلتر من نظام حقوق النشر بتاع فيسبوك.

**ليه مش بيبي شارك؟** تسجيل Pinkfong محمي بحقوق ملكية وبيتراقب بقوة على ميتا (وصلوا للمحكمة العليا الكورية فيه). لو استخدمناه، فيسبوك غالبًا هيكتم الريل أو يقلّل وصوله. أي أغنية أطفال تجارية تانية نفس المشكلة — وده سبب وجود اللحن المتولّد ده أصلًا.

## الكابشن الجاهز للنشر على فيسبوك

> لعبة الحلقات الملوّنة… أبسط لعبة وأقوى تدريب 🌈
>
> في التدريب ده الطفل بيشتغل على أكتر من مهارة في نفس الوقت:
> • تقوية العضلات الدقيقة للأصابع (مسك وإفلات)
> • تناسق العين مع اليد
> • تمييز الأحجام والترتيب من الأكبر للأصغر
> • الانتباه المشترك والتبادل (دوري… ودورك)
> • إكمال المهمة لآخرها من غير تشتّت
>
> كل طفل له إيقاعه الخاص، والصبر والتكرار سرّ التقدّم 💛
>
> احفظوا الفيديو وشاركوه مع أم محتاجة تشوفه.
>
> #تنمية_مهارات #مهارات_حركية #تنمية_مهارات_الطفل #العضلات_الدقيقة
> #انتباه_وتركيز #تخاطب #تأخر_الكلام #أطفال #توحد #تربية #تعليم_الأطفال

## قبل النشر

- اتأكدي إن عندك **موافقة ولي الأمر** على نشر فيديو فيه الطفل.
- لو عايزة تخفي هوية الطفل أكتر، ممكن نضيف بلور على الوش.
- أفضل وقت نشر لمحتوى الأمهات: من ٨ لـ ١١ مساءً بتوقيت القاهرة.

---

## إعادة البناء / التعديل — Rebuilding

```bash
./scripts/build_reel.sh [SOURCE] [OUTPUT]
```

Requires `ffmpeg` (with libass built against HarfBuzz and FriBidi) and the
`fonts-lemonada` package. No Python dependencies beyond the standard library.

### Files

- `scripts/build_reel.sh` — the whole pipeline; denoise, grade, speed, captions, end card, mix, encode.
- `scripts/gen_subs.py` — writes the burned-in caption tracks (`main.ass`, `outro.ass`).
- `scripts/make_music.py` — synthesises the background track.
- `build/source.mov` — the original footage.

### Editing the on-screen captions

Caption text and timings live in the `CAPTIONS` list in `scripts/gen_subs.py`,
as `(start, end, line1, line2)`. Titles are `TITLE_MAIN` / `TITLE_SUB`, and the
end card is `OUTRO_LINES` / `OUTRO_CTA`. Re-run `build_reel.sh` after editing.

Two constraints:

- Keep every ASS style's `Spacing` at `0`. A non-zero value makes libass lay out
  glyphs individually, which silently disables Arabic shaping and bidi — the
  text renders backwards in disconnected letterforms.
- Captions may only describe what is visible. The source has no audio, so any
  claim about what was said during the session is unverifiable.

### Tuning

Knobs at the top of `build_reel.sh`: `SPEED` (pacing), `OUTRO` (end card
length), `XFADE` (dissolve), and `GRADE` (the colour correction string).
Encode quality is `-crf` / `-preset` near the bottom.

To add a clinic name or handle to the reel, add a persistent `Dialogue` line to
the header of `build_main()` in `gen_subs.py`.
