import { Table, Text } from '@mantine/core';
import { ReactNode } from 'react';
import { Order, OrderDepth, Trade } from '../../models.ts';
import { getAskColor, getBidColor } from '../../utils/colors.ts';
import { formatNumber } from '../../utils/format.ts';
import { OrderDepthTableSpreadRow } from './OrderDepthTableSpreadRow.tsx';

export interface OrderDepthTableProps {
  orderDepth: OrderDepth;
  ownOrders: Order[];
  ownTrades: Trade[];
  marketTrades: Trade[];
}

export function OrderDepthTable({ orderDepth, ownOrders, ownTrades, marketTrades }: OrderDepthTableProps): ReactNode {
  const rows: ReactNode[] = [];

  const askTradeMap = new Map<number, number>();
  const bidTradeMap = new Map<number, number>();
  for (const trade of ownOrders) {
    if (trade.quantity < 0) {
      askTradeMap.set(trade.price, (askTradeMap.get(trade.price) ?? 0) + trade.quantity);
    } else {
      bidTradeMap.set(trade.price, (bidTradeMap.get(trade.price) ?? 0) + trade.quantity);
    }
  }

  const ownTradesBidMap = new Map<number, number>();
  const ownTradesAskMap = new Map<number, number>();
  for (const trade of ownTrades) {
    if (trade.buyer === 'SUBMISSION') {
      ownTradesAskMap.set(trade.price, (ownTradesAskMap.get(trade.price) ?? 0) + trade.quantity);
    } else {
      ownTradesBidMap.set(trade.price, (ownTradesBidMap.get(trade.price) ?? 0) + trade.quantity);
    }
  }

  const marketTradesBidMap = new Map<number, number>();
  const marketTradesAskMap = new Map<number, number>();
  for (const trade of marketTrades) {
    if (trade.buyer === 'SUBMISSION') {
      marketTradesAskMap.set(trade.price, (marketTradesAskMap.get(trade.price) ?? 0) + trade.quantity);
    } else {
      marketTradesBidMap.set(trade.price, (marketTradesBidMap.get(trade.price) ?? 0) + trade.quantity);
    }
  }

  const prices = [
    ...new Set(
      Object.keys(orderDepth.sellOrders)
        .map(Number)
        .concat(Object.keys(orderDepth.buyOrders).map(Number))
        .concat(Array.from(askTradeMap.keys()))
        .concat(Array.from(bidTradeMap.keys()))
        .concat(Array.from(ownTradesBidMap.keys()))
        .concat(Array.from(ownTradesAskMap.keys()))
        .concat(Array.from(marketTradesBidMap.keys()))
        .concat(Array.from(marketTradesAskMap.keys())),
    ),
  ].sort((a, b) => b - a);

  for (let i = 0; i < prices.length; i++) {
    const price = prices[i];

    if (i > 0 && prices[i - 1] - price > 1) {
      rows.push(<OrderDepthTableSpreadRow key={`${price}-ask-spread`} spread={prices[i - 1] - price} />);
    }

    // orders
    const askVolume = orderDepth.sellOrders[price] ?? 0;
    const bidVolume = orderDepth.buyOrders[price] ?? 0;
    const askOrderVolume = askTradeMap.get(price) ?? 0;
    const bidOrderVolume = bidTradeMap.get(price) ?? 0;

    const hasAsk = Math.abs(askVolume) + Math.abs(askOrderVolume) > 0;
    const hasBid = Math.abs(bidVolume) + Math.abs(bidOrderVolume) > 0;

    // trades
    const marketAskTradeVolume = marketTradesAskMap.get(price) ?? 0;
    const marketBidTradeVolume = marketTradesBidMap.get(price) ?? 0;
    const ownAskTradeVolume = ownTradesAskMap.get(price) ?? 0;
    const ownBidTradeVolume = ownTradesBidMap.get(price) ?? 0;

    const hasAskTrade = Math.abs(marketAskTradeVolume) + Math.abs(ownAskTradeVolume) > 0;
    const hasBidTrade = Math.abs(marketBidTradeVolume) + Math.abs(ownBidTradeVolume) > 0;

    rows.push(
      <Table.Tr key={`${price}-ask`}>
        <Table.Td
          style={{
            backgroundColor: hasAskTrade ? getAskColor(0.1) : 'transparent',
          }}
        >
          {hasAskTrade
            ? formatNumber(marketAskTradeVolume) + (ownAskTradeVolume ? ` (+${formatNumber(ownAskTradeVolume)})` : '')
            : ''}
        </Table.Td>
        <Table.Td
          style={{
            backgroundColor: hasBid ? getBidColor(0.1) : 'transparent',
            textAlign: 'right',
          }}
        >
          {hasBid ? formatNumber(bidVolume) + (bidOrderVolume ? ` (+${formatNumber(bidOrderVolume)})` : '') : ''}
        </Table.Td>
        <Table.Td style={{ textAlign: 'center' }}>{formatNumber(price)}</Table.Td>
        <Table.Td
          style={{
            backgroundColor: hasAsk ? getAskColor(0.1) : 'transparent',
          }}
        >
          {hasAsk ? formatNumber(askVolume) + (askOrderVolume ? ` (${formatNumber(askOrderVolume)})` : '') : ''}
        </Table.Td>
        <Table.Td
          style={{
            backgroundColor: hasBidTrade ? getBidColor(0.1) : 'transparent',
            textAlign: 'right',
          }}
        >
          {hasBidTrade
            ? formatNumber(marketBidTradeVolume) + (ownBidTradeVolume ? ` (+${formatNumber(ownBidTradeVolume)})` : '')
            : ''}
        </Table.Td>
      </Table.Tr>,
    );
  }

  if (rows.length === 0) {
    return <Text>Timestamp has no order depth</Text>;
  }

  return (
    <Table withColumnBorders horizontalSpacing={8} verticalSpacing={4}>
      <Table.Thead>
        <Table.Tr>
          <Table.Th style={{ textAlign: 'right' }}>Bought</Table.Th>
          <Table.Th style={{ textAlign: 'right' }}>Bid volume</Table.Th>
          <Table.Th style={{ textAlign: 'center' }}>Price</Table.Th>
          <Table.Th>Ask volume</Table.Th>
          <Table.Th>Sold</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>{rows}</Table.Tbody>
    </Table>
  );
}
