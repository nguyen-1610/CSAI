# PR Checklist

Checklist nay dung cho cac dot sua tiep theo. Muc tieu la giu scope ro, verify du, va docs khop voi code that.

## Context da chot

- App hien tai dung Flask + HTML/CSS/JavaScript thuan
- Khong co React, Vite, Tailwind, hay build step frontend
- Runtime la single-user, in-memory
- Tree view da bo han khoi san pham

## Truoc khi merge

- [ ] Scope PR ro rang va nho vua du
- [ ] Khong pha API contract giua frontend va backend
- [ ] Khong doi `id` trong `templates/index.html` neu chua update JS binding
- [ ] Cap nhat docs neu thay doi behavior chinh thuc

## Verify bat buoc

- [ ] `python -m compileall app.py algorithms core`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `GET /` tra `200`

Neu may co Node.js:

- [ ] `node --check static/js/app.js`
- [ ] `node --check static/js/visualize.js`
- [ ] `node --check static/js/race.js`

## Smoke test tay

### Visualize

- [ ] Chon thuat toan va bam `Run`
- [ ] `Pause` / `Continue`
- [ ] `Step` / `Step Back`
- [ ] Keo tha start, end, checkpoint
- [ ] `Basic Maze`
- [ ] `Weighted Maze`
- [ ] Checkpoint route van hien end marker

### Race

- [ ] Chon it nhat 2 thuat toan
- [ ] Bam `Race`
- [ ] Runner panels render dung
- [ ] Result Matrix hien du du lieu
- [ ] Charts khong de chu/legend de len nhau
- [ ] Checkpoint route animate duoc doan start->checkpoint va checkpoint->end

## Ghi chu

- `.venv/` la local virtual environment, khong duoc commit
- Neu repo chua co `.venv`, tao bang `python -m venv .venv`
