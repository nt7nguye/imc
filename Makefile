
run:
	cd round$(round) && \
	poetry run prosperity3bt $(trader).py $(round) --no-progress --out backtests/$(trader).log && \
	cd ..
