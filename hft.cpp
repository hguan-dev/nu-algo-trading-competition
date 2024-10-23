#include "Strategy.hpp"
#include <iostream>
#include <numeric>
#include <algorithm>
#include <thread>
#include <chrono>

Strategy::Strategy()
    : capital(100000.0f), position("none"), position_size(0.0f),
      window_size(10), max_position_fraction(0.5f),
      entry_threshold(0.003f), exit_threshold(-0.003f),
      max_orders_per_minute(30), best_bid(-1.0f), best_ask(-1.0f) {}

void Strategy::on_trade_update(Ticker ticker, Side side, float price, float quantity) {
    if (ticker != Ticker::BTC) return;

    std::cout << "Trade update: " << static_cast<int>(ticker) << " "
              << static_cast<int>(side) << " " << price << " " << quantity << "\n";

    price_history.push_back(price);
    if (price_history.size() > window_size * 2) {
        price_history.erase(price_history.begin());
    }

    execute_trade();
}

void Strategy::on_orderbook_update(Ticker ticker, Side side, float price, float quantity) {
    if (ticker != Ticker::BTC) return;

    if (side == Side::BUY) {
        if (quantity == 0 && best_bid == price) {
            best_bid = -1.0f;
        } else if (best_bid < 0 || price > best_bid) {
            best_bid = price;
        }
    } else if (side == Side::SELL) {
        if (quantity == 0 && best_ask == price) {
            best_ask = -1.0f;
        } else if (best_ask < 0 || price < best_ask) {
            best_ask = price;
        }
    }

    if (best_bid > 0 && best_ask > 0) {
        float mid_price = (best_bid + best_ask) / 2.0f;
        price_history.push_back(mid_price);
        if (price_history.size() > window_size * 2) {
            price_history.erase(price_history.begin());
        }

        execute_trade();
    }
}

void Strategy::on_account_update(Ticker ticker, Side side, float price, float quantity, float capital_remaining) {
    if (ticker != Ticker::BTC) return;

    std::cout << "Account update: " << static_cast<int>(ticker) << " "
              << static_cast<int>(side) << " " << price << " " << quantity << " "
              << capital_remaining << "\n";

    capital = capital_remaining;
    if (side == Side::BUY) {
        position_size += quantity;
        position = "long";
    } else if (side == Side::SELL) {
        position_size -= quantity;
        if (position_size <= 0) {
            position = "none";
        }
    }
}

void Strategy::execute_trade() {
    if (price_history.size() < window_size) return;

    float slope = calculate_slope();
    std::cout << "Regression slope: " << slope << "\n";

    float current_price = price_history.back();

    if (position == "none" && slope > entry_threshold) {
        float investment = capital * max_position_fraction;
        float quantity = investment / current_price;
        if (place_market_order_with_rate_limit(Side::BUY, Ticker::BTC, quantity)) {
            std::cout << "Entering long position: Bought " << quantity
                      << " BTC at " << current_price << "\n";
        }
    } else if (position == "long" && slope < exit_threshold) {
        float quantity = position_size;
        if (place_market_order_with_rate_limit(Side::SELL, Ticker::BTC, quantity)) {
            std::cout << "Exiting long position: Sold " << quantity
                      << " BTC at " << current_price << "\n";
        }
    }
}

float Strategy::calculate_slope() {
    int n = price_history.size();
    std::vector<float> x(n), y(n);
    std::iota(x.begin(), x.end(), 0);
    y = price_history;

    float x_mean = std::accumulate(x.begin(), x.end(), 0.0f) / n;
    float y_mean = std::accumulate(y.begin(), y.end(), 0.0f) / n;

    float numerator = 0.0f;
    float denominator = 0.0f;
    for (int i = 0; i < n; ++i) {
        numerator += (x[i] - x_mean) * (y[i] - y_mean);
        denominator += (x[i] - x_mean) * (x[i] - x_mean);
    }

    return (denominator != 0) ? (numerator / denominator) : 0.0f;
}

bool Strategy::place_market_order_with_rate_limit(Side side, Ticker ticker, float quantity) {
    auto now = std::chrono::steady_clock::now();
    order_timestamps.erase(std::remove_if(order_timestamps.begin(), order_timestamps.end(),
        [now](const auto& t) { return std::chrono::duration_cast<std::chrono::seconds>(now - t).count() >= 60; }),
        order_timestamps.end());

    if (order_timestamps.size() >= max_orders_per_minute) {
        std::cout << "Rate limit exceeded: Cannot place market order at this time.\n";
        return false;
    }

    if (place_market_order(side, ticker, quantity)) {
        order_timestamps.push_back(now);
        std::cout << "Placed MARKET order: " << static_cast<int>(side) << " "
                  << static_cast<int>(ticker) << " " << quantity << "\n";
        return true;
    } else {
        std::cout << "Failed to place MARKET order: " << static_cast<int>(side) << " "
                  << static_cast<int>(ticker) << " " << quantity << "\n";
        return false;
    }
}
