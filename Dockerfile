FROM rust:1.98-bookworm AS build
WORKDIR /build
COPY Cargo.toml Cargo.lock ./
COPY server ./server
COPY world ./world
RUN cargo build --release --locked

FROM debian:bookworm-slim
WORKDIR /app
RUN mkdir /app/data && chown 10001:10001 /app/data
COPY --from=build /build/target/release/valhalla-server /usr/local/bin/valhalla-server
COPY client ./client
USER 10001:10001
ENV VALHALLA_BIND=0.0.0.0:8080 VALHALLA_DB=/app/data/valhalla.sqlite
EXPOSE 8080
CMD ["valhalla-server"]
