import { Table, Text } from '@mantine/core';
import { ReactNode } from 'react';
import { Order, OrderDepth } from '../../models.ts';
import { getAskColor, getBidColor } from '../../utils/colors.ts';
import { formatNumber } from '../../utils/format.ts';
import { OrderDepthTableSpreadRow } from './OrderDepthTableSpreadRow.tsx';

export interface OrderDepthTableProps {
  orderDepth: OrderDepth;
  ownOrders: Order[];
}

export function OrderDepthTable({ orderDepth, ownOrders }: OrderDepthTableProps): ReactNode {
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

  const prices = [
    ...new Set(
      Object.keys(orderDepth.sellOrders)
        .map(Number)
        .concat(Object.keys(orderDepth.buyOrders).map(Number))
        .concat(Array.from(askTradeMap.keys()))
        .concat(Array.from(bidTradeMap.keys())),
    ),
  ].sort((a, b) => b - a);

  for (let i = 0; i < prices.length; i++) {
    const price = prices[i];

    if (i > 0 && prices[i - 1] - price > 1) {
      rows.push(<OrderDepthTableSpreadRow key={`${price}-ask-spread`} spread={prices[i - 1] - price} />);
    }

    const askVolume = orderDepth.sellOrders[price] ?? 0;
    const bidVolume = orderDepth.buyOrders[price] ?? 0;
    const askTradeVolume = askTradeMap.get(price) ?? 0;
    const bidTradeVolume = bidTradeMap.get(price) ?? 0;

    rows.push(
      <Table.Tr key={`${price}-ask`}>
        <Table.Td
          style={{
            backgroundColor: Math.abs(bidVolume) + Math.abs(bidTradeVolume) > 0 ? getBidColor(0.1) : 'transparent',
            textAlign: 'right',
          }}
        >
          {formatNumber(bidVolume)}
          {bidTradeVolume ? ` (+${formatNumber(bidTradeVolume)})` : ''}
        </Table.Td>
        <Table.Td style={{ textAlign: 'center' }}>{formatNumber(price)}</Table.Td>
        <Table.Td
          style={{
            backgroundColor: Math.abs(askVolume) + Math.abs(askTradeVolume) > 0 ? getAskColor(0.1) : 'transparent',
          }}
        >
          {formatNumber(askVolume)}
          {askTradeVolume ? ` (${formatNumber(askTradeVolume)})` : ''}
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
          <Table.Th style={{ textAlign: 'right' }}>Bid volume</Table.Th>
          <Table.Th style={{ textAlign: 'center' }}>Price</Table.Th>
          <Table.Th>Ask volume</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>{rows}</Table.Tbody>
    </Table>
  );
}
