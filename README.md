# Simple Elforbrug 
custom_component for Home Assistant.

## Opretter forbindelse til Eloverblik API og henter data om ens elforbrug.

Opretter 3 sensor. 
```
  Daily:
    - Daily Usage
    - Metering Point
    - Metering date
    - 1 days ago
    - 2 days ago
    - 3 days ago
    - 4 days ago
    - 5 days ago
    - 6 days ago
    - 7 days ago

  Monthly:
    - Daily Usage
    - Metering Point
    - Metering date

  Yearly:
    - Daily Usage
    - Metering Point
    - Metering date
```

## API
En hurtig guide til API adgang.
Link: [Eloverblik.dk](https://www.eloverblik.dk)

<img width="800" height="568" alt="Skærmbillede 13-08-2025 kl  08 19 25 AM" src="https://github.com/user-attachments/assets/bf801d2f-e4b4-4f82-bb7c-e9e9df4ebd51" />

<img width="800" height="566" alt="Skærmbillede 13-08-2025 kl  08 20 35 AM" src="https://github.com/user-attachments/assets/ce32f480-97bd-4407-90aa-832c2b45ae72" />

<img width="800" height="561" alt="Skærmbillede 13-08-2025 kl  08 20 58 AM" src="https://github.com/user-attachments/assets/ce0261e4-ad0c-4d2c-b241-2d1954852a59" />

## INSTALLATION

1. Download Simple-Elforbrug
2. Placer filerne i config/custom_component/simple_elforbrug...
3. Genstart Home Assistant
4. Instillinger -> Enheder & tjenester -> + Tilføj integration
5. Søg Simple Elforbrug og følg guiden.
6. ENJOY!

## Actions.

 - set_unit: Skifter mellem kWh og MWh
 - update_energy: Opdater manuelt eller via automation hvis der ønsker oftere opdateringer. Standard er 1 times opdaterings interval

## Example i Custom:button-card
Der er mulighed for at undgå at bruge apexcharts-card og bare "nøjes" med custom:button-card og dermed have MANGE flere muligheder for at lave et custom design:
Her er et hurtigt eksempel i et søjle diagram.

```
type: custom:button-card
entity: sensor.simple_elforbrug_daily
name: Elforbrug
show_state: true
show_icon: false
show_name: true
state_display: |
  [[[ return 'Forbrug: ' + entity.state ]]]
styles:
  grid:
    - grid-template-areas: |
        "n s"
        "chart chart"
        "chart_names chart_names"
    - grid-template-columns: auto
    - grid-template-rows: 10px 130px auto
  card:
    - height: 200px
    - padding: 10px
  name:
    - font-size: 14px
    - justify-self: start
    - align-self: center
  state:
    - font-size: 14px
    - justify-self: end
    - align-self: center
  custom_fields:
    chart:
      - display: flex
      - align-items: flex-end
      - height: 130px
    chart_names:
      - display: flex
      - align-items: center
      - height: 40px
custom_fields:
  chart: |
    [[[
      const attrs = entity.attributes;
      const values = [
        attrs["7 days ago"],
        attrs["6 days ago"],
        attrs["5 days ago"],
        attrs["4 days ago"],
        attrs["3 days ago"],
        attrs["2 days ago"],
        attrs["1 days ago"],
        parseFloat(entity.state)
      ];

      const maxVal = Math.max(...values);
      if (maxVal <= 0) return "";

      return `
        <div style="display:flex;
                    align-items:flex-end;
                    height:100px;
                    width:100%;
                    gap:4px;">
          ${values.map(v => `
            <div style="
              flex:1;
              height:${(v/maxVal)*100}%;
              background-color: red;
              border-radius: 3px;
            " title="${v.toFixed(3)}"></div>
          `).join('')}
        </div>
      `;
    ]]]
  chart_names: |
    [[[
      const labels = ["7d","6d","5d","4d","3d","2d","1d","Nu"];
      return `
        <div style="display:flex;
                    width:100%;gap:4px;">
          ${labels.map(l => `
            <div style="flex:1;
                        text-align:center;
                        font-size:10px;
                        color: white;">${l}</div>
          `).join('')}
        </div>
      `;
    ]]]
```
<img width="510" height="205" alt="Skærmbillede 14-08-2025 kl  08 11 57 AM" src="https://github.com/user-attachments/assets/a8c18e89-a367-404f-830c-3d723c261c0b" />




### Authors
Contributors names and contact info

 - [Jesper Halberg](https://www.facebook.com/jesperrielhalberg/)

### Donate crypto:
XRP Ripple: raxGy2N7mzDBECVQMsE66aNS7tCMNdMnDg 

![IMG_0411](https://github.com/user-attachments/assets/e2cf3a3a-eac9-4c1d-a66f-c279fbd801fe)

Bitcoin: bc1q3edhsll33d8hzu82c4hh0v0x8gpxlvkzttfx42

![bitcoin](https://github.com/user-attachments/assets/71a2fd51-c602-4e1a-8fa8-5c9e16e390d1)


