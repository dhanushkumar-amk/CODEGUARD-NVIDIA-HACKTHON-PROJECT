import React from 'react';

interface CardItem {
  id: number;
  title: string;
  description: string;
}

const items: CardItem[] = [
  { id: 1, title: 'Accessibility First', description: 'Inclusive design for everyone.' },
  { id: 2, title: 'Automated Auditing', description: 'High-speed WCAG 2.2 detection.' },
];

export const CardList: React.FC = () => {
  return (
    <section aria-labelledby="cards-section-title" className="cards-grid">
      <h2 id="cards-section-title">Core Principles</h2>
      <div className="card-container">
        {items.map((item) => (
          <article key={item.id} className="card-item">
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
};

export default CardList;
