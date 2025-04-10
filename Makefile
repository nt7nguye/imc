
run:
	cd round$(round) && \
	poetry run prosperity3bt $(trader).py $(round) --match-trades worse --no-progress --out backtests/$(trader).log && \
	cd ..
